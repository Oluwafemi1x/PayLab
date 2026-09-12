import httpx
import pytest

from paylab.engine import trigger_event
from paylab.models import TriggerRequest


@pytest.mark.asyncio
async def test_retries_after_http_500() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, request=request)
        return httpx.Response(200, request=request)

    request = TriggerRequest(
        provider="paystack",
        event="charge.success",
        target_url="http://merchant.test/webhook",
        secret="secret",
        retry_count=2,
        retry_delay_seconds=0,
    )
    result = await trigger_event(
        request,
        transport=httpx.MockTransport(handler),
        record_history=False,
    )

    assert [item.status_code for item in result.deliveries] == [500, 200]
    assert result.deliveries[-1].retry_index == 1


@pytest.mark.asyncio
async def test_does_not_retry_client_rejection() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request)

    request = TriggerRequest(
        provider="paystack",
        event="charge.success",
        target_url="http://merchant.test/webhook",
        secret="secret",
        retry_count=3,
    )
    result = await trigger_event(
        request,
        transport=httpx.MockTransport(handler),
        record_history=False,
    )

    assert len(result.deliveries) == 1
    assert result.deliveries[0].status_code == 401
