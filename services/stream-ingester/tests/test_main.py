"""Tests for stream-ingester FastAPI endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from shared.health import HealthChecker
from stream_ingester.main import app


def _txn_payload(**overrides) -> dict:
    defaults = {
        "txn_id": str(uuid4()),
        "user_id": "user-123",
        "amount": 99.99,
        "currency": "USD",
        "merchant_id": "merch-456",
        "mcc": "5411",
        "timestamp": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        "latitude": 40.7128,
        "longitude": -74.0060,
        "device_fingerprint": "fp-abc",
        "ip_address": "192.168.1.1",
    }
    defaults.update(overrides)
    return defaults


@pytest.mark.asyncio
async def test_health():
    app.state.health_checker = HealthChecker(service_name="stream-ingester")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_post_transactions_returns_202():
    mock_publisher = AsyncMock()
    mock_publisher.publish.return_value = b"1234-0"

    with patch("stream_ingester.main._publisher", mock_publisher):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = _txn_payload()
            resp = await client.post("/transactions", json=payload)

    assert resp.status_code == 202
    body = resp.json()
    assert body["txn_id"] == payload["txn_id"]
    assert body["status"] == "accepted"


@pytest.mark.asyncio
async def test_post_transactions_calls_publisher():
    mock_publisher = AsyncMock()
    mock_publisher.publish.return_value = b"1234-0"

    with patch("stream_ingester.main._publisher", mock_publisher):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = _txn_payload()
            await client.post("/transactions", json=payload)

    mock_publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_post_transactions_invalid_body():
    mock_publisher = AsyncMock()

    with patch("stream_ingester.main._publisher", mock_publisher):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/transactions", json={"bad": "data"})

    assert resp.status_code == 422
    mock_publisher.publish.assert_not_called()
