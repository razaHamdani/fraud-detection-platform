import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_post_chargeback():
    from feedback_service.main import app
    from feedback_service import state

    mock_processor = AsyncMock()
    mock_processor.process = AsyncMock(return_value=True)
    state.processor = mock_processor

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/feedback/chargeback", json={
            "txn_id": str(uuid.uuid4()),
            "reason": "unauthorized",
        })

    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"


@pytest.mark.asyncio
async def test_post_chargeback_no_decision():
    from feedback_service.main import app
    from feedback_service import state

    mock_processor = AsyncMock()
    mock_processor.process = AsyncMock(return_value=False)
    state.processor = mock_processor

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/feedback/chargeback", json={
            "txn_id": str(uuid.uuid4()),
            "reason": "unauthorized",
        })

    assert resp.status_code == 200
    assert resp.json()["status"] == "partial"
