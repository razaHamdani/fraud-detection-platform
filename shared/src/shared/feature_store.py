"""Redis-backed feature store with sliding window counters."""

import time
from typing import Any, Optional
from uuid import UUID

FEATURE_TTL_SECONDS = 3600


class RedisFeatureStore:
    """Store and retrieve transaction features in Redis."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def record_and_count(
        self,
        key: str,
        window_seconds: int,
        member: str,
        timestamp: Optional[float] = None,
    ) -> int:
        """Add member to sorted set and return count within window.

        Uses zadd + zremrangebyscore + zcard in a pipeline.
        Sets TTL to window_seconds * 2.
        """
        now = timestamp or time.time()
        min_score = now - window_seconds

        async with self._redis.pipeline() as pipe:
            pipe.zadd(key, {member: now})
            pipe.zremrangebyscore(key, "-inf", min_score)
            pipe.zcard(key)
            pipe.expire(key, window_seconds * 2)
            results = await pipe.execute()

        return results[2]  # zcard result

    async def store_features(self, txn_id: UUID, features: dict) -> None:
        """Store feature dict as a Redis hash with TTL."""
        key = f"features:{txn_id}"
        await self._redis.hset(key, mapping=features)
        await self._redis.expire(key, FEATURE_TTL_SECONDS)

    async def get_features(self, txn_id: UUID) -> dict:
        """Retrieve feature hash for a transaction."""
        return await self._redis.hgetall(f"features:{txn_id}")
