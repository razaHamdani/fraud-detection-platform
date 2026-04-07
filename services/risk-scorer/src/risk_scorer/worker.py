"""Stream consumer worker that scores enriched transactions."""

import asyncio
import json

import asyncpg
import redis.asyncio as aioredis
import structlog

from shared.models import FeatureSet, ScoringWeights
from shared.streams import RedisStreamConsumer, RedisStreamPublisher
from risk_scorer.scoring import compute_risk_score
from risk_scorer.rules import apply_rules, DEFAULT_RULES

logger = structlog.get_logger()


async def store_decision_pg(pool: asyncpg.Pool, decision_data: dict) -> None:
    """Persist decision to PostgreSQL."""
    await pool.execute(
        """
        INSERT INTO decisions (txn_id, risk_score, decision, breakdown_json, rules_triggered)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (txn_id) DO NOTHING
        """,
        decision_data["txn_id"],
        decision_data["risk_score"],
        decision_data["decision"],
        json.dumps(decision_data["breakdown"]),
        decision_data["rules_triggered"],
    )


async def store_transaction_pg(pool: asyncpg.Pool, txn_data: dict) -> None:
    """Persist transaction to PostgreSQL (idempotent)."""
    await pool.execute(
        """
        INSERT INTO transactions (txn_id, user_id, amount, currency, merchant_id, mcc, timestamp,
                                  latitude, longitude, device_fingerprint, ip_address)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (txn_id) DO NOTHING
        """,
        txn_data["txn_id"], txn_data["user_id"], txn_data["amount"],
        txn_data["currency"], txn_data["merchant_id"], txn_data["mcc"],
        txn_data["timestamp"], txn_data["latitude"], txn_data["longitude"],
        txn_data["device_fingerprint"], txn_data["ip_address"],
    )


async def run_worker(
    redis: aioredis.Redis,
    pg_pool: asyncpg.Pool,
    weights: ScoringWeights,
) -> None:
    consumer = RedisStreamConsumer(
        redis,
        stream="stream:enriched_transactions",
        group="risk-scorer",
        consumer_name="worker-1",
    )
    await consumer.ensure_group()
    publisher = RedisStreamPublisher(redis_client=redis)

    logger.info("risk_scorer_worker_started")

    while True:
        messages = await consumer.read(count=10, block=1000)
        for msg_id, data in messages:
            try:
                features_json = json.loads(data[b"features_json"].decode())
                feature_set = FeatureSet(**features_json)

                decision = compute_risk_score(feature_set, weights)
                decision = apply_rules(decision, feature_set, DEFAULT_RULES)

                # Store in Postgres
                decision_dict = decision.model_dump()
                decision_dict["breakdown"] = [b.model_dump() for b in decision.breakdown]
                await store_decision_pg(pg_pool, {
                    "txn_id": decision.txn_id,
                    "risk_score": float(decision.risk_score),
                    "decision": decision.decision.value,
                    "breakdown": decision_dict["breakdown"],
                    "rules_triggered": decision.rules_triggered,
                })

                # Publish to decisions stream
                await publisher.publish("stream:decisions", {
                    "txn_id": str(decision.txn_id),
                    "risk_score": str(decision.risk_score),
                    "decision": decision.decision.value,
                })

                # Cache decision in Redis for fast lookup
                await redis.hset(f"decision:{decision.txn_id}", mapping={
                    "risk_score": str(decision.risk_score),
                    "decision": decision.decision.value,
                    "breakdown_json": json.dumps(decision_dict["breakdown"]),
                    "rules_triggered": json.dumps(decision.rules_triggered),
                })
                await redis.expire(f"decision:{decision.txn_id}", 3600)

                await consumer.ack(msg_id)
                logger.info("transaction_scored", txn_id=str(decision.txn_id),
                           score=decision.risk_score, decision=decision.decision.value)

            except Exception as e:
                logger.error("scoring_failed", msg_id=msg_id, error=str(e))
