"""Redis Streams abstraction with protocol classes for future swapping."""

from typing import Any, Protocol, runtime_checkable

from redis.exceptions import ResponseError


@runtime_checkable
class StreamPublisher(Protocol):
    """Protocol for publishing messages to a stream."""

    async def publish(self, stream: str, data: dict) -> Any: ...


@runtime_checkable
class StreamConsumer(Protocol):
    """Protocol for consuming messages from a stream."""

    async def read(self, count: int, block: int) -> list[tuple]: ...

    async def ack(self, stream: str, message_id: Any) -> None: ...


class RedisStreamPublisher:
    """Publish messages to a Redis Stream via xadd."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def publish(self, stream: str, data: dict) -> Any:
        return await self._redis.xadd(stream, data)


class RedisStreamConsumer:
    """Consume messages from a Redis Stream via xreadgroup."""

    def __init__(
        self, redis_client: Any, group: str, consumer_name: str
    ) -> None:
        self._redis = redis_client
        self._group = group
        self._consumer_name = consumer_name

    async def read(self, count: int = 10, block: int = 5000) -> list[tuple]:
        result = await self._redis.xreadgroup(
            self._group,
            self._consumer_name,
            streams={">": ">"},
            count=count,
            block=block,
        )
        if not result:
            return []
        # Flatten: result is [[stream_name, [(id, data), ...]]]
        messages = []
        for _stream_name, entries in result:
            messages.extend(entries)
        return messages

    async def ack(self, stream: str, message_id: Any) -> None:
        await self._redis.xack(stream, self._group, message_id)

    async def ensure_group(self, stream: str, start_id: str = "0") -> None:
        """Create consumer group, ignoring if it already exists."""
        try:
            await self._redis.xgroup_create(stream, self._group, id=start_id, mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
