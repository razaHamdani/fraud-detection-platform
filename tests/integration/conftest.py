"""Integration test fixtures requiring Docker Compose services."""

import asyncio
import os

import asyncpg
import pytest
import redis.asyncio as aioredis


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_client():
    url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    client = aioredis.from_url(url)
    yield client
    await client.aclose()


@pytest.fixture(scope="session")
async def pg_pool():
    dsn = os.environ.get(
        "POSTGRES_DSN",
        "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_detection",
    )
    pool = await asyncpg.create_pool(dsn)
    yield pool
    await pool.close()
