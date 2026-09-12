import asyncio
import time

import httpx

from paylab.models import DeliveryAttempt, TriggerRequest, TriggerResponse
from paylab.providers import PROVIDERS


async def trigger_event(request: TriggerRequest) -> TriggerResponse:
    adapter = PROVIDERS[request.provider]
    built = adapter.build_event(
        request.event,
        request.secret,
        request.metadata,
        invalid_signature=request.invalid_signature,
    )

    if request.delay_seconds:
        await asyncio.sleep(request.delay_seconds)

    deliveries: list[DeliveryAttempt] = []
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for attempt_number in range(1, request.duplicate + 1):
            started = time.perf_counter()
            try:
                response = await client.post(
                    str(request.target_url),
                    content=built.body,
                    headers=built.headers,
                )
                latency = round((time.perf_counter() - started) * 1000, 2)
                deliveries.append(
                    DeliveryAttempt(
                        attempt=attempt_number,
                        status_code=response.status_code,
                        latency_ms=latency,
                    )
                )
            except httpx.HTTPError as exc:
                latency = round((time.perf_counter() - started) * 1000, 2)
                deliveries.append(
                    DeliveryAttempt(
                        attempt=attempt_number,
                        latency_ms=latency,
                        error=str(exc),
                    )
                )

    return TriggerResponse(
        event_id=built.event_id,
        provider=request.provider,
        event=request.event,
        target_url=str(request.target_url),
        duplicate=request.duplicate,
        invalid_signature=request.invalid_signature,
        deliveries=deliveries,
    )
