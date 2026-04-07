import json
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.hgetall = AsyncMock(return_value={
        b"risk_score": b"0.25",
        b"decision": b"APPROVE",
        b"breakdown_json": b'[{"category":"velocity","sub_score":0.1,"weight":0.3,"contribution":0.03}]',
        b"rules_triggered": b"[]",
    })
    return mock


@pytest.mark.asyncio
async def test_get_decision(mock_redis):
    from decision_api.main import app
    from decision_api import state
    state.redis = mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        txn_id = str(uuid.uuid4())
        resp = await client.get(f"/transactions/{txn_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "APPROVE"
    assert float(body["risk_score"]) < 0.3


@pytest.mark.asyncio
async def test_get_decision_not_found(mock_redis):
    from decision_api.main import app
    from decision_api import state
    mock_redis.hgetall = AsyncMock(return_value={})
    state.redis = mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        txn_id = str(uuid.uuid4())
        resp = await client.get(f"/transactions/{txn_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_explain_endpoint(mock_redis):
    from decision_api.main import app
    from decision_api import state
    state.redis = mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        txn_id = str(uuid.uuid4())
        resp = await client.get(f"/explain/{txn_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "breakdown" in body
    assert len(body["breakdown"]) > 0
