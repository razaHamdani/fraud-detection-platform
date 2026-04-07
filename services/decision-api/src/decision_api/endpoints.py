"""REST API endpoints for decision lookup and explainability."""
import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException

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
