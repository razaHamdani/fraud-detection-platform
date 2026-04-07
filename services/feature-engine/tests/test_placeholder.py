from httpx import ASGITransport, AsyncClient
import pytest

from shared.health import HealthChecker
from feature_engine.main import app


@pytest.mark.asyncio
async def test_health():
    app.state.health_checker = HealthChecker(service_name="feature-engine")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
