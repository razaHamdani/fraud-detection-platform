"""Chargeback processing and weight adjustment."""

import json
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as aioredis

from shared.logging import get_logger
from shared.models import Chargeback, ScoringWeights

logger = get_logger()


def adjust_weights(
    current: ScoringWeights,
    breakdown: list[dict],
    alpha: float = 0.1,
) -> ScoringWeights:
    """Adjust weights via EMA based on which categories contributed to missed fraud."""
    scores = {b["category"]: b["sub_score"] for b in breakdown}
    total_score = sum(scores.values()) or 1.0

    # Target weights proportional to sub_scores (categories that detected fraud get more weight)
    target = {cat: score / total_score for cat, score in scores.items()}

    new = ScoringWeights(
        velocity=current.velocity * (1 - alpha) + target.get("velocity", current.velocity) * alpha,
        geo=current.geo * (1 - alpha) + target.get("geo", current.geo) * alpha,
        device=current.device * (1 - alpha) + target.get("device", current.device) * alpha,
        graph=current.graph * (1 - alpha) + target.get("graph", current.graph) * alpha,
    )

    # Normalize to sum to 1.0
    total = new.velocity + new.geo + new.device + new.graph
    return ScoringWeights(
        velocity=round(new.velocity / total, 4),
        geo=round(new.geo / total, 4),
        device=round(new.device / total, 4),
        graph=round(new.graph / total, 4),
    )


class ChargebackProcessor:
    def __init__(self, pg_pool: asyncpg.Pool, redis: aioredis.Redis):
        self._pg = pg_pool
        self._redis = redis

    async def process(self, cb: Chargeback) -> bool:
        log = logger.bind(txn_id=str(cb.txn_id))

        # Store chargeback
        await self._pg.execute(
            """
            INSERT INTO chargebacks (chargeback_id, txn_id, reason, reported_at)
            VALUES ($1, $2, $3, $4)
            """,
            cb.chargeback_id, cb.txn_id, cb.reason, cb.reported_at,
        )

        # Look up original decision
        row = await self._pg.fetchrow(
            "SELECT breakdown_json FROM decisions WHERE txn_id = $1",
            cb.txn_id,
        )
        if not row:
            log.warning("chargeback_no_decision")
            return False

        breakdown = json.loads(row["breakdown_json"])

        # Load current weights
        weight_rows = await self._pg.fetch("SELECT category, weight FROM scoring_weights")
        if weight_rows:
            current = ScoringWeights(**{r["category"]: float(r["weight"]) for r in weight_rows})
        else:
            current = ScoringWeights()

        new_weights = adjust_weights(current, breakdown)

        # Update weights in Postgres
        for category in ["velocity", "geo", "device", "graph"]:
            await self._pg.execute(
                """
                UPDATE scoring_weights SET weight = $1, updated_at = NOW()
                WHERE category = $2
                """,
                float(getattr(new_weights, category)),
                category,
            )

        # Publish weight update to Redis for hot-reload
        await self._redis.publish("channel:weight_updates", json.dumps(new_weights.model_dump()))

        log.info("chargeback_processed", new_weights=new_weights.model_dump())
        return True
