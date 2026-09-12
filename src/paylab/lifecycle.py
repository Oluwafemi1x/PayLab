from __future__ import annotations

import asyncio
import secrets

import httpx

from paylab.engine import trigger_event
from paylab.history import EventHistory
from paylab.models import LifecycleRequest, LifecycleResponse, LifecycleStep, TriggerRequest
from paylab.stream import EventStream

DEFAULT_LIFECYCLES: dict[str, tuple[str, ...]] = {
    "paystack": ("charge.success", "refund.processed"),
    "stripe": ("payment_intent.succeeded", "charge.refunded"),
    "flutterwave": ("charge.completed", "refund.completed"),
}


def lifecycle_events(request: LifecycleRequest) -> list[str]:
    if request.events:
        return list(request.events)

    defaults = DEFAULT_LIFECYCLES.get(request.provider)
    if defaults is None:
        raise ValueError(
            f"Provider '{request.provider}' has no default lifecycle; supply events explicitly."
        )
    return list(defaults)


async def run_lifecycle(
    request: LifecycleRequest,
    *,
    history: EventHistory | None = None,
    stream: EventStream | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    record_history: bool = True,
    publish_stream: bool = True,
) -> LifecycleResponse:
    events = lifecycle_events(request)
    if request.out_of_order:
        events.reverse()

    lifecycle_id = f"lc_{secrets.token_hex(8)}"
    steps: list[LifecycleStep] = []

    for index, event_name in enumerate(events, start=1):
        metadata = {
            **request.metadata,
            "paylab_lifecycle_id": lifecycle_id,
            "paylab_lifecycle_step": index,
            "paylab_lifecycle_total": len(events),
        }
        response = await trigger_event(
            TriggerRequest(
                provider=request.provider,
                event=event_name,
                target_url=request.target_url,
                secret=request.secret,
                metadata=metadata,
                timeout_seconds=request.timeout_seconds,
            ),
            history=history,
            stream=stream,
            transport=transport,
            record_history=record_history,
            publish_stream=publish_stream,
        )
        status_codes = [delivery.status_code for delivery in response.deliveries]
        acknowledged = bool(status_codes) and all(
            code is not None and 200 <= code < 300 for code in status_codes
        )
        steps.append(
            LifecycleStep(
                step=index,
                event=event_name,
                event_id=response.event_id,
                acknowledged=acknowledged,
                status_codes=status_codes,
            )
        )
        if index < len(events) and request.interval_seconds:
            await asyncio.sleep(request.interval_seconds)

    return LifecycleResponse(
        lifecycle_id=lifecycle_id,
        provider=request.provider,
        target_url=str(request.target_url),
        out_of_order=request.out_of_order,
        steps=steps,
    )
