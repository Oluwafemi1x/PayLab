import asyncio
import time

import httpx

from paylab.history import EventHistory, get_history_store
from paylab.models import DeliveryAttempt, TriggerRequest, TriggerResponse
from paylab.providers import PROVIDERS


def _should_retry(status_code: int | None, error: str | None) -> bool:
    return error is not None or (status_code is not None and status_code >= 500)


async def trigger_event(
    request: TriggerRequest,
    *,
    history: EventHistory | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    record_history: bool = True,
) -> TriggerResponse:
    adapter = PROVIDERS[request.provider]
    built = adapter.build_event(
        request.event,
        request.secret,
        request.metadata,
        invalid_signature=request.invalid_signature,
    )

    headers = dict(built.headers)
    if request.fault != "none":
        headers["x-paylab-fault"] = request.fault
        headers["x-paylab-fault-delay"] = str(max(request.timeout_seconds * 3, 0.2))

    if request.delay_seconds:
        await asyncio.sleep(request.delay_seconds)

    deliveries: list[DeliveryAttempt] = []
    timeout = httpx.Timeout(request.timeout_seconds)
    attempt_number = 0
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        transport=transport,
    ) as client:
        for delivery_index in range(1, request.duplicate + 1):
            for retry_index in range(0, request.retry_count + 1):
                attempt_number += 1
                started = time.perf_counter()
                status_code: int | None = None
                error: str | None = None
                try:
                    response = await client.post(
                        str(request.target_url),
                        content=built.body,
                        headers=headers,
                    )
                    status_code = response.status_code
                except httpx.HTTPError as exc:
                    error = str(exc)

                latency = round((time.perf_counter() - started) * 1000, 2)
                deliveries.append(
                    DeliveryAttempt(
                        attempt=attempt_number,
                        delivery_index=delivery_index,
                        retry_index=retry_index,
                        status_code=status_code,
                        latency_ms=latency,
                        error=error,
                    )
                )

                if not _should_retry(status_code, error) or retry_index >= request.retry_count:
                    break
                if request.retry_delay_seconds:
                    await asyncio.sleep(request.retry_delay_seconds)

            if delivery_index < request.duplicate and request.delivery_interval_seconds:
                await asyncio.sleep(request.delivery_interval_seconds)

    result = TriggerResponse(
        event_id=built.event_id,
        provider=request.provider,
        event=request.event,
        target_url=str(request.target_url),
        duplicate=request.duplicate,
        invalid_signature=request.invalid_signature,
        retry_count=request.retry_count,
        fault=request.fault,
        deliveries=deliveries,
    )

    if record_history:
        (history or get_history_store()).record(request, result)
    return result
