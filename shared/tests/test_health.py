"""Tests for shared health check utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_health_check_all_healthy():
    from shared.health import HealthChecker

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_pg = AsyncMock()
    mock_pg.fetchval = AsyncMock(return_value=1)

    checker = HealthChecker(redis=mock_redis, pg_pool=mock_pg)
    result = await checker.check()
    assert result["status"] == "healthy"
    assert result["redis"] == "ok"
    assert result["postgres"] == "ok"


@pytest.mark.asyncio
async def test_health_check_redis_down():
    from shared.health import HealthChecker

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
    mock_pg = AsyncMock()
    mock_pg.fetchval = AsyncMock(return_value=1)

    checker = HealthChecker(redis=mock_redis, pg_pool=mock_pg)
    result = await checker.check()
    assert result["status"] == "degraded"
    assert result["redis"] == "error"


@pytest.mark.asyncio
async def test_health_check_neo4j():
    from shared.health import HealthChecker

    mock_neo4j = MagicMock()
    mock_neo4j.verify_connectivity = MagicMock()

    checker = HealthChecker(neo4j_driver=mock_neo4j, service_name="feature-engine")
    result = await checker.check()
    assert result["status"] == "healthy"
    assert result["neo4j"] == "ok"
    assert result["service"] == "feature-engine"


@pytest.mark.asyncio
async def test_health_check_no_dependencies():
    from shared.health import HealthChecker

    checker = HealthChecker(service_name="test")
    result = await checker.check()
    assert result["status"] == "healthy"
    assert result["service"] == "test"
