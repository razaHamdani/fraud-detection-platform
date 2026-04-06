"""Redis-backed feature store with sliding window counters."""

import time
from typing import Any, Optional
from uuid import UUID

FEATURE_TTL_SECONDS = 3600

# Lua script for atomic sliding window counter
_RECORD_AND_COUNT_SCRIPT = """
local key = KEYS[1]
local member = ARGV[1]
local score = tonumber(ARGV[2])
local cutoff = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

redis.call('ZADD', key, score, member)
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
redis.call('EXPIRE', key, ttl)
return count
"""


class RedisFeatureStore:
    """Store and retrieve transaction features in Redis."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client
        self._record_and_count_sha: Optional[str] = None

    async def _ensure_script(self) -> str:
        """Register the Lua script and cache its SHA."""
        if self._record_and_count_sha is None:
            self._record_and_count_sha = await self._redis.script_load(
                _RECORD_AND_COUNT_SCRIPT
            )
        return self._record_and_count_sha

    async def record_and_count(
        self,
        key: str,
        window_seconds: int,
        member: str,
        timestamp: Optional[float] = None,
    ) -> int:
        """Add member to sorted set and return count within window.

        Uses an atomic Lua script to ZADD + ZREMRANGEBYSCORE + ZCARD + EXPIRE.
        Sets TTL to window_seconds * 2.
        """
        now = timestamp or time.time()
        cutoff = now - window_seconds
        ttl = window_seconds * 2

        sha = await self._ensure_script()
        return await self._redis.evalsha(sha, 1, key, member, now, cutoff, ttl)

    async def store_features(self, txn_id: UUID, features: dict) -> None:
        """Store feature dict as a Redis hash with TTL."""
        key = f"features:{txn_id}"
        async with self._redis.pipeline() as pipe:
            await pipe.hset(key, mapping=features)
            await pipe.expire(key, FEATURE_TTL_SECONDS)
            await pipe.execute()

    async def get_features(self, txn_id: UUID) -> dict:
        """Retrieve feature hash for a transaction."""
        return await self._redis.hgetall(f"features:{txn_id}")
