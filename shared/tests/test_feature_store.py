"""Tests for shared.feature_store — Redis feature store with sliding windows."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock
from uuid import uuid4

import pytest

from shared.feature_store import FEATURE_TTL_SECONDS, RedisFeatureStore


class TestRedisFeatureStore:
    @pytest.fixture
    def pipeline(self):
        p = AsyncMock()
        p.zadd = MagicMock()
        p.zremrangebyscore = MagicMock()
        p.zcard = MagicMock()
        p.expire = MagicMock()
        p.execute = AsyncMock(return_value=[1, 0, 5])
        p.__aenter__ = AsyncMock(return_value=p)
        p.__aexit__ = AsyncMock(return_value=False)
        return p

    @pytest.fixture
    def redis_client(self, pipeline):
        client = AsyncMock()
        client.pipeline = MagicMock(return_value=pipeline)
        client.hset = AsyncMock()
        client.expire = AsyncMock()
        client.hgetall = AsyncMock(return_value={b"amount_zscore": b"2.1"})
        return client

    @pytest.fixture
    def store(self, redis_client):
        return RedisFeatureStore(redis_client)

    async def test_record_and_count(self, store, redis_client, pipeline):
        count = await store.record_and_count("user:u1:txn_5min", 300, "txn-abc")
        assert count == 5  # from pipeline.execute return_value[2]
        pipeline.execute.assert_awaited_once()

    async def test_record_and_count_with_timestamp(self, store, pipeline):
        count = await store.record_and_count(
            "user:u1:txn_5min", 300, "txn-abc", timestamp=1700000000.0
        )
        assert count == 5

    async def test_store_features(self, store, redis_client):
        txn_id = uuid4()
        features = {"amount_zscore": 2.1, "txn_count_5min": 3}
        await store.store_features(txn_id, features)
        redis_client.hset.assert_awaited_once()
        redis_client.expire.assert_awaited_once()
        # Check TTL argument
        call_args = redis_client.expire.call_args
        assert call_args[0][1] == FEATURE_TTL_SECONDS

    async def test_get_features(self, store, redis_client):
        txn_id = uuid4()
        result = await store.get_features(txn_id)
        redis_client.hgetall.assert_awaited_once_with(f"features:{txn_id}")
        assert result == {b"amount_zscore": b"2.1"}

    def test_feature_ttl_constant(self):
        assert FEATURE_TTL_SECONDS == 3600
