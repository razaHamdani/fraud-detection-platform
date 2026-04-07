import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_post_transaction_sync_scoring():
    from decision_api.main import app
    from decision_api import state

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value=b"1234-0")
    mock_redis.hgetall = AsyncMock(return_value={
        b"risk_score": b"0.25",
        b"decision": b"APPROVE",
        b"breakdown_json": b"[]",
        b"rules_triggered": b"[]",
    })
    state.redis = mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/transactions", json={
            "user_id": "user_001",
            "amount": 99.99,
            "currency": "USD",
            "merchant_id": "merch_001",
            "mcc": "5411",
            "timestamp": "2026-04-04T12:00:00Z",
            "latitude": 40.7128,
            "longitude": -74.006,
            "device_fingerprint": "fp_abc",
            "ip_address": "192.168.1.1",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert "decision" in body
