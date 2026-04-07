from httpx import ASGITransport, AsyncClient
import pytest

from shared.health import HealthChecker
from feedback_service.main import app
from feedback_service import state


@pytest.mark.asyncio
async def test_health():
    state.health_checker = HealthChecker(service_name="feedback-service")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
