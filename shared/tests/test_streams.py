"""Tests for shared.streams — Redis Streams abstraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.streams import (
    RedisStreamConsumer,
    RedisStreamPublisher,
    StreamConsumer,
    StreamPublisher,
)


class TestRedisStreamPublisher:
    @pytest.fixture
    def redis_client(self):
        client = AsyncMock()
        client.xadd = AsyncMock(return_value=b"1234567890-0")
        return client

    @pytest.fixture
    def publisher(self, redis_client):
        return RedisStreamPublisher(redis_client)

    async def test_publish(self, publisher, redis_client):
        result = await publisher.publish("txn_stream", {"txn_id": "abc"})
        redis_client.xadd.assert_awaited_once_with("txn_stream", {"txn_id": "abc"})
        assert result == b"1234567890-0"

    def test_implements_protocol(self, publisher):
        assert isinstance(publisher, StreamPublisher)


class TestRedisStreamConsumer:
    @pytest.fixture
    def redis_client(self):
        client = AsyncMock()
        client.xreadgroup = AsyncMock(return_value=[
            [b"txn_stream", [(b"1-0", {b"txn_id": b"abc"})]]
        ])
        client.xack = AsyncMock(return_value=1)
        client.xgroup_create = AsyncMock()
        return client

    @pytest.fixture
    def consumer(self, redis_client):
        return RedisStreamConsumer(
            redis_client, group="fraud-group", consumer_name="worker-1"
        )

    async def test_read(self, consumer, redis_client):
        result = await consumer.read(count=10, block=1000)
        redis_client.xreadgroup.assert_awaited_once()
        assert len(result) == 1
        assert result[0] == (b"1-0", {b"txn_id": b"abc"})

    async def test_ack(self, consumer, redis_client):
        await consumer.ack("txn_stream", b"1-0")
        redis_client.xack.assert_awaited_once_with("txn_stream", "fraud-group", b"1-0")

    async def test_ensure_group_creates_group(self, consumer, redis_client):
        await consumer.ensure_group("txn_stream")
        redis_client.xgroup_create.assert_awaited_once()

    async def test_ensure_group_ignores_exists_error(self, consumer, redis_client):
        from redis.exceptions import ResponseError

        redis_client.xgroup_create = AsyncMock(
            side_effect=ResponseError("BUSYGROUP Consumer Group name already exists")
        )
        # Should not raise
        await consumer.ensure_group("txn_stream")

    def test_implements_protocol(self, consumer):
        assert isinstance(consumer, StreamConsumer)
