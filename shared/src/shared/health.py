"""Health check utilities for all services."""

from __future__ import annotations

import redis.asyncio as aioredis


class HealthChecker:
    def __init__(
        self,
        redis: aioredis.Redis | None = None,
        pg_pool=None,
        neo4j_driver=None,
        service_name: str = "unknown",
    ):
        self._redis = redis
        self._pg = pg_pool
        self._neo4j = neo4j_driver
        self._service_name = service_name

    async def check(self) -> dict:
        results = {"service": self._service_name}
        all_ok = True

        if self._redis:
            try:
                await self._redis.ping()
                results["redis"] = "ok"
            except Exception:
                results["redis"] = "error"
                all_ok = False

        if self._pg:
            try:
                await self._pg.fetchval("SELECT 1")
                results["postgres"] = "ok"
            except Exception:
                results["postgres"] = "error"
                all_ok = False

        if self._neo4j:
            try:
                self._neo4j.verify_connectivity()
                results["neo4j"] = "ok"
            except Exception:
                results["neo4j"] = "error"
                all_ok = False

        results["status"] = "healthy" if all_ok else "degraded"
        return results
