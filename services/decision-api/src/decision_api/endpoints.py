"""REST API endpoints for decision lookup and explainability."""
import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException

from shared.models import Transaction
from shared.streams import RedisStreamPublisher
from decision_api import state

router = APIRouter()


@router.get("/transactions/{txn_id}")
async def get_decision(txn_id: uuid.UUID):
    cached = await state.redis.hgetall(f"decision:{txn_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="Decision not found")
    return {
        "txn_id": str(txn_id),
        "risk_score": cached[b"risk_score"].decode(),
        "decision": cached[b"decision"].decode(),
    }


@router.get("/explain/{txn_id}")
async def explain_decision(txn_id: uuid.UUID):
    cached = await state.redis.hgetall(f"decision:{txn_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="Decision not found")
    breakdown = json.loads(cached[b"breakdown_json"].decode())
    rules = json.loads(cached[b"rules_triggered"].decode())
    return {
        "txn_id": str(txn_id),
        "risk_score": cached[b"risk_score"].decode(),
        "decision": cached[b"decision"].decode(),
        "breakdown": breakdown,
        "rules_triggered": rules,
    }


@router.post("/transactions")
async def score_transaction(txn: Transaction):
    """Synchronous scoring: publish to stream, poll for result, return decision."""
    publisher = RedisStreamPublisher(redis_client=state.redis)

    data = {
        "txn_id": str(txn.txn_id),
        "user_id": txn.user_id,
        "amount": str(txn.amount),
        "currency": txn.currency,
        "merchant_id": txn.merchant_id,
        "mcc": txn.mcc,
        "timestamp": txn.timestamp.isoformat(),
        "latitude": str(txn.latitude),
        "longitude": str(txn.longitude),
        "device_fingerprint": txn.device_fingerprint,
        "ip_address": txn.ip_address,
    }
    await publisher.publish("stream:raw_transactions", data)

    # Poll Redis for decision (up to 50ms)
    txn_id_str = str(txn.txn_id)
    for _ in range(10):  # 10 x 5ms = 50ms max
        cached = await state.redis.hgetall(f"decision:{txn_id_str}")
        if cached:
            breakdown = json.loads(cached[b"breakdown_json"].decode())
            rules = json.loads(cached[b"rules_triggered"].decode())
            return {
                "txn_id": txn_id_str,
                "risk_score": cached[b"risk_score"].decode(),
                "decision": cached[b"decision"].decode(),
                "breakdown": breakdown,
                "rules_triggered": rules,
            }
        await asyncio.sleep(0.005)

    raise HTTPException(status_code=202, detail="Scoring in progress, poll GET /transactions/{txn_id}")
