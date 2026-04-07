import uuid

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_rate_limiting_allows_normal_traffic():
    from decision_api.main import app
    from decision_api import state

    state.redis = AsyncMock()
    state.redis.hgetall = AsyncMock(return_value={
        b"risk_score": b"0.2", b"decision": b"APPROVE",
        b"breakdown_json": b"[]", b"rules_triggered": b"[]",
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiting_blocks_excessive_traffic():
    from decision_api.middleware import RateLimitMiddleware
    from decision_api import state
    from fastapi import FastAPI

    # Build a small app with tight rate limit for testing
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, max_requests=3, window_seconds=60)

    mock_redis = AsyncMock()
    mock_redis.hgetall = AsyncMock(return_value={
        b"risk_score": b"0.2", b"decision": b"APPROVE",
        b"breakdown_json": b"[]", b"rules_triggered": b"[]",
    })
    state.redis = mock_redis

    @test_app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        for _ in range(3):
            resp = await client.get("/test")
            assert resp.status_code == 200

        # 4th request should be rate limited
        resp = await client.get("/test")
        assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limiting_skips_health():
    from decision_api.middleware import RateLimitMiddleware
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60)

    @test_app.get("/health")
    async def health():
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Health should never be rate limited
        for _ in range(5):
            resp = await client.get("/health")
            assert resp.status_code == 200
