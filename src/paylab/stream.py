from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
from typing import Any, Protocol


class EventStreamBackend(Protocol):
    async def publish(self, payload: dict[str, Any]) -> None: ...

    def subscribe(self) -> AbstractAsyncContextManager[asyncio.Queue[dict[str, Any]]]: ...


class EventStream:
    """In-process fan-out stream used by the live dashboard and WebSocket API."""

    def __init__(self, *, max_queue_size: int = 100) -> None:
        self.max_queue_size = max_queue_size
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    async def publish(self, payload: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            _put_latest(queue, payload)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.max_queue_size)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class RedisEventStream:
    """Redis Pub/Sub event stream for sharing live events across PayLab processes."""

    def __init__(
        self,
        redis_url: str,
        *,
        channel: str = "paylab:events",
        max_queue_size: int = 100,
    ) -> None:
        if not redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("PAYLAB_REDIS_URL must use redis:// or rediss://")
        try:
            from redis import asyncio as redis_asyncio
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Redis streaming requires the optional dependency: "
                'pip install "paylab-dev[redis]"'
            ) from exc

        self.redis_url = redis_url
        self.channel = channel
        self.max_queue_size = max_queue_size
        self._client = redis_asyncio.from_url(redis_url, decode_responses=True)
        self._subscriber_count = 0

    async def publish(self, payload: dict[str, Any]) -> None:
        await self._client.publish(
            self.channel,
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        )

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.max_queue_size)
        pubsub = self._client.pubsub()
        await pubsub.subscribe(self.channel)
        self._subscriber_count += 1
        listener = asyncio.create_task(self._listen(pubsub, queue))
        try:
            yield queue
        finally:
            listener.cancel()
            with suppress(asyncio.CancelledError):
                await listener
            await pubsub.unsubscribe(self.channel)
            await pubsub.aclose()
            self._subscriber_count -= 1

    async def _listen(self, pubsub: Any, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not isinstance(raw, str):
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                _put_latest(queue, payload)

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def subscriber_count(self) -> int:
        return self._subscriber_count


def _put_latest(
    queue: asyncio.Queue[dict[str, Any]],
    payload: dict[str, Any],
) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        pass


_event_stream: EventStreamBackend | None = None


def _build_event_stream() -> EventStreamBackend:
    redis_url = os.getenv("PAYLAB_REDIS_URL", "").strip()
    if redis_url:
        channel = os.getenv("PAYLAB_REDIS_CHANNEL", "paylab:events").strip() or "paylab:events"
        return RedisEventStream(redis_url, channel=channel)
    return EventStream()


def get_event_stream() -> EventStreamBackend:
    global _event_stream
    if _event_stream is None:
        _event_stream = _build_event_stream()
    return _event_stream


def _reset_event_stream_for_tests() -> None:
    global _event_stream
    _event_stream = None
