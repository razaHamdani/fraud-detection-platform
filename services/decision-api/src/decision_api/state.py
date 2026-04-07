"""Mutable service state for dependency injection."""
import redis.asyncio as aioredis
import asyncpg

redis: aioredis.Redis | None = None
pg_pool: asyncpg.Pool | None = None
