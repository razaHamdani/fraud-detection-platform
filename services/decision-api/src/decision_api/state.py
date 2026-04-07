"""Mutable service state for dependency injection."""
import redis.asyncio as aioredis
import asyncpg

from shared.health import HealthChecker

redis: aioredis.Redis | None = None
pg_pool: asyncpg.Pool | None = None
health_checker: HealthChecker | None = None
