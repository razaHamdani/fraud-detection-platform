"""Tests for shared.feature_store — Redis feature store with sliding windows."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from shared.feature_store import FEATURE_TTL_SECONDS, RedisFeatureStore


class TestRedisFeatureStore:
    @pytest.fixture
    def pipeline(self):
        p = AsyncMock()
        p.hset = AsyncMock()
        p.expire = AsyncMock()
        p.execute = AsyncMock(return_value=[True, True])
        p.__aenter__ = AsyncMock(return_value=p)
        p.__aexit__ = AsyncMock(return_value=False)
        return p

    @pytest.fixture
    def redis_client(self, pipeline):
        client = AsyncMock()
        client.pipeline = MagicMock(return_value=pipeline)
        client.script_load = AsyncMock(return_value="abc123sha")
        client.evalsha = AsyncMock(return_value=5)
        client.hgetall = AsyncMock(return_value={b"amount_zscore": b"2.1"})
        return client

    @pytest.fixture
    def store(self, redis_client):
        return RedisFeatureStore(redis_client)

    async def test_record_and_count(self, store, redis_client):
        count = await store.record_and_count("user:u1:txn_5min", 300, "txn-abc")
        assert count == 5
        redis_client.script_load.assert_awaited_once()
        redis_client.evalsha.assert_awaited_once()
        # Verify the key and member are passed correctly
        call_args = redis_client.evalsha.call_args
        assert call_args[0][0] == "abc123sha"  # SHA
        assert call_args[0][1] == 1  # numkeys
        assert call_args[0][2] == "user:u1:txn_5min"  # key
        assert call_args[0][3] == "txn-abc"  # member

    async def test_record_and_count_with_timestamp(self, store, redis_client):
        count = await store.record_and_count(
            "user:u1:txn_5min", 300, "txn-abc", timestamp=1700000000.0
        )
        assert count == 5
        call_args = redis_client.evalsha.call_args
        assert call_args[0][4] == 1700000000.0  # score (now)
        assert call_args[0][5] == 1700000000.0 - 300  # cutoff
        assert call_args[0][6] == 600  # ttl = window_seconds * 2

    async def test_record_and_count_caches_script_sha(self, store, redis_client):
        """Script SHA should be loaded once and reused on subsequent calls."""
        await store.record_and_count("k1", 300, "m1")
        await store.record_and_count("k2", 300, "m2")
        redis_client.script_load.assert_awaited_once()
        assert redis_client.evalsha.await_count == 2

    async def test_store_features(self, store, redis_client, pipeline):
        txn_id = uuid4()
        features = {"amount_zscore": 2.1, "txn_count_5min": 3}
        await store.store_features(txn_id, features)
        pipeline.hset.assert_awaited_once()
        pipeline.expire.assert_awaited_once()
        pipeline.execute.assert_awaited_once()
        # Check TTL argument
        call_args = pipeline.expire.call_args
        assert call_args[0][1] == FEATURE_TTL_SECONDS

    async def test_get_features(self, store, redis_client):
        txn_id = uuid4()
        result = await store.get_features(txn_id)
        redis_client.hgetall.assert_awaited_once_with(f"features:{txn_id}")
        assert result == {b"amount_zscore": b"2.1"}

    def test_feature_ttl_constant(self):
        assert FEATURE_TTL_SECONDS == 3600
