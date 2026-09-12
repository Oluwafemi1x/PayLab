from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from uuid import uuid4

import httpx
import pytest

import paylab.stream as stream_module
from paylab.engine import trigger_event
from paylab.models import TriggerRequest

pytest.importorskip("redis")


REDIS_URL = os.getenv("PAYLAB_TEST_REDIS_URL", "")


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Redis integration URL is not configured")
async def test_redis_stream_cross_process_publish() -> None:
    channel = f"paylab:test:{uuid4().hex}"
    subscriber = stream_module.RedisEventStream(REDIS_URL, channel=channel)
    code = (
        "import asyncio; "
        "from paylab.stream import RedisEventStream; "
        f"s=RedisEventStream({REDIS_URL!r}, channel={channel!r}); "
        "async def main():\n"
        "    await s.publish({'type':'cross-process','value':42})\n"
        "    await s.aclose()\n"
        "asyncio.run(main())"
    )

    try:
        async with subscriber.subscribe() as queue:
            await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-c", code],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = await asyncio.wait_for(queue.get(), timeout=5)
    finally:
        await subscriber.aclose()

    assert payload == {"type": "cross-process", "value": 42}


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Redis integration URL is not configured")
async def test_trigger_streams_safe_event_through_redis() -> None:
    channel = f"paylab:test:{uuid4().hex}"
    publisher = stream_module.RedisEventStream(REDIS_URL, channel=channel)
    subscriber = stream_module.RedisEventStream(REDIS_URL, channel=channel)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)

    try:
        async with subscriber.subscribe() as queue:
            result = await trigger_event(
                TriggerRequest(
                    provider="paystack",
                    event="charge.success",
                    target_url="http://merchant.test/webhook",
                    secret="redis-super-secret",
                ),
                transport=httpx.MockTransport(handler),
                record_history=False,
                stream=publisher,
            )
            payload = await asyncio.wait_for(queue.get(), timeout=5)
    finally:
        await publisher.aclose()
        await subscriber.aclose()

    assert payload["type"] == "delivery.completed"
    assert payload["event"]["event_id"] == result.event_id
    assert "secret" not in payload["event"]
    assert "redis-super-secret" not in str(payload)


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Redis integration URL is not configured")
async def test_stream_factory_selects_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYLAB_REDIS_URL", REDIS_URL)
    stream_module._reset_event_stream_for_tests()

    stream = stream_module.get_event_stream()

    assert isinstance(stream, stream_module.RedisEventStream)
    await stream.aclose()
    stream_module._reset_event_stream_for_tests()
