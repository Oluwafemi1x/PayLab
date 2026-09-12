import httpx
import pytest

from paylab.engine import trigger_event
from paylab.models import TriggerRequest
from paylab.stream import EventStream


@pytest.mark.asyncio
async def test_stream_fans_out_to_subscribers() -> None:
    stream = EventStream()
    async with stream.subscribe() as first, stream.subscribe() as second:
        await stream.publish({"type": "test", "value": 1})
        assert await first.get() == {"type": "test", "value": 1}
        assert await second.get() == {"type": "test", "value": 1}
    assert stream.subscriber_count == 0


@pytest.mark.asyncio
async def test_trigger_publishes_safe_live_event() -> None:
    stream = EventStream()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)

    async with stream.subscribe() as queue:
        result = await trigger_event(
            TriggerRequest(provider="paystack", event="charge.success", target_url="http://merchant.test/webhook", secret="super-secret"),
            transport=httpx.MockTransport(handler),
            record_history=False,
            stream=stream,
        )
        payload = await queue.get()

    assert payload["type"] == "delivery.completed"
    assert payload["event"]["event_id"] == result.event_id
    assert "secret" not in payload["event"]
