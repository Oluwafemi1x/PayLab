from __future__ import annotations

from dataclasses import dataclass

import httpx

from paylab.engine import trigger_event
from paylab.models import (
    ChaosRequest,
    ChaosResponse,
    ChaosScenarioResult,
    TriggerRequest,
    TriggerResponse,
)


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    description: str
    points: int


BASELINE = ScenarioSpec("baseline_delivery", "A correctly signed payment webhook is accepted.", 25)
DUPLICATE = ScenarioSpec(
    "duplicate_delivery",
    "The same event can be delivered repeatedly without transport failure.",
    25,
)
INVALID_SIGNATURE = ScenarioSpec(
    "invalid_signature", "A forged webhook signature is rejected.", 25
)
DELAYED = ScenarioSpec(
    "delayed_delivery", "A valid webhook is still accepted after a delivery delay.", 25
)
RETRY_500 = ScenarioSpec(
    "retry_after_500",
    "The receiver recovers after an initial HTTP 500 and accepts a retry.",
    25,
)
TIMEOUT_RECOVERY = ScenarioSpec(
    "timeout_recovery",
    "The receiver recovers after a timed-out delivery and accepts a retry.",
    25,
)
IDEMPOTENCY = ScenarioSpec(
    "business_idempotency",
    "Repeated delivery produces one business side effect.",
    25,
)


def _successful(delivery_status: int | None) -> bool:
    return delivery_status is not None and 200 <= delivery_status < 300


def _evidence(response: TriggerResponse) -> str:
    parts: list[str] = []
    for attempt in response.deliveries:
        prefix = (
            f"attempt {attempt.attempt} "
            f"(delivery={attempt.delivery_index}, retry={attempt.retry_index})"
        )
        if attempt.error:
            parts.append(f"{prefix}: ERROR {attempt.error}")
        else:
            parts.append(f"{prefix}: HTTP {attempt.status_code} ({attempt.latency_ms} ms)")
    return "; ".join(parts)


def _result(spec: ScenarioSpec, passed: bool, evidence: str) -> ChaosScenarioResult:
    return ChaosScenarioResult(
        name=spec.name,
        description=spec.description,
        passed=passed,
        points=spec.points if passed else 0,
        max_points=spec.points,
        evidence=evidence,
    )


def evaluate_baseline(response: TriggerResponse) -> ChaosScenarioResult:
    passed = bool(response.deliveries) and all(
        _successful(item.status_code) for item in response.deliveries
    )
    return _result(BASELINE, passed, _evidence(response))


def evaluate_duplicate(response: TriggerResponse, expected_deliveries: int) -> ChaosScenarioResult:
    successful_delivery_indexes = {
        item.delivery_index for item in response.deliveries if _successful(item.status_code)
    }
    passed = len(successful_delivery_indexes) == expected_deliveries and expected_deliveries > 1
    return _result(
        DUPLICATE,
        passed,
        (
            f"event_id={response.event_id}; {_evidence(response)}. "
            "HTTP acknowledgement alone does not prove business-level idempotency."
        ),
    )


def evaluate_invalid_signature(response: TriggerResponse) -> ChaosScenarioResult:
    statuses = [item.status_code for item in response.deliveries if item.status_code is not None]
    passed = bool(statuses) and all(status in {400, 401, 403} for status in statuses)
    return _result(INVALID_SIGNATURE, passed, _evidence(response))


def evaluate_delayed(response: TriggerResponse) -> ChaosScenarioResult:
    passed = bool(response.deliveries) and all(
        _successful(item.status_code) for item in response.deliveries
    )
    return _result(DELAYED, passed, _evidence(response))


def evaluate_retry_after_500(response: TriggerResponse) -> ChaosScenarioResult:
    statuses = [item.status_code for item in response.deliveries]
    passed = (
        len(statuses) >= 2
        and statuses[0] is not None
        and statuses[0] >= 500
        and _successful(statuses[-1])
        and response.deliveries[-1].retry_index > 0
    )
    return _result(RETRY_500, passed, _evidence(response))


def evaluate_timeout_recovery(response: TriggerResponse) -> ChaosScenarioResult:
    passed = (
        len(response.deliveries) >= 2
        and response.deliveries[0].error is not None
        and _successful(response.deliveries[-1].status_code)
        and response.deliveries[-1].retry_index > 0
    )
    return _result(TIMEOUT_RECOVERY, passed, _evidence(response))


def evaluate_idempotency_probe(
    *, event_id: str, expected_deliveries: int, payload: dict[str, object]
) -> ChaosScenarioResult:
    side_effect_count = payload.get("side_effect_count")
    deliveries_received = payload.get("deliveries_received")
    passed = side_effect_count == 1 and isinstance(deliveries_received, int) and (
        deliveries_received >= expected_deliveries
    )
    return _result(
        IDEMPOTENCY,
        passed,
        (
            f"event_id={event_id}; deliveries_received={deliveries_received}; "
            f"side_effect_count={side_effect_count}"
        ),
    )


def grade_for(score: int, max_score: int = 100) -> str:
    if max_score <= 0:
        return "D"
    percentage = (score / max_score) * 100
    if percentage >= 90:
        return "A"
    if percentage >= 75:
        return "B"
    if percentage >= 50:
        return "C"
    return "D"


async def _run_probe(
    probe_url: str, event_id: str, expected_deliveries: int
) -> ChaosScenarioResult:
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.get(probe_url, params={"event_id": event_id})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return _result(IDEMPOTENCY, False, f"probe failed: {exc}")
    if not isinstance(payload, dict):
        return _result(IDEMPOTENCY, False, "probe response must be a JSON object")
    return evaluate_idempotency_probe(
        event_id=event_id,
        expected_deliveries=expected_deliveries,
        payload=payload,
    )


async def run_checkout_chaos(request: ChaosRequest) -> ChaosResponse:
    common = {
        "provider": request.provider,
        "event": request.event,
        "target_url": request.target_url,
        "secret": request.secret,
        "metadata": {"paylab_scenario": "checkout", **request.metadata},
    }

    baseline_response = await trigger_event(TriggerRequest(**common))
    duplicate_response = await trigger_event(
        TriggerRequest(**common, duplicate=request.duplicate_count)
    )
    invalid_response = await trigger_event(TriggerRequest(**common, invalid_signature=True))
    delayed_response = await trigger_event(
        TriggerRequest(**common, delay_seconds=request.delay_seconds)
    )

    scenarios = [
        evaluate_baseline(baseline_response),
        evaluate_duplicate(duplicate_response, request.duplicate_count),
        evaluate_invalid_signature(invalid_response),
        evaluate_delayed(delayed_response),
    ]

    if request.enable_fault_injection:
        retry_common = {
            **common,
            "retry_count": request.retry_count,
            "retry_delay_seconds": request.retry_delay_seconds,
        }
        retry_500_response = await trigger_event(
            TriggerRequest(**retry_common, fault="fail-once")
        )
        timeout_response = await trigger_event(
            TriggerRequest(
                **retry_common,
                fault="timeout-once",
                timeout_seconds=request.timeout_seconds,
            )
        )
        scenarios.extend(
            [
                evaluate_retry_after_500(retry_500_response),
                evaluate_timeout_recovery(timeout_response),
            ]
        )

    if request.probe_url is not None:
        scenarios.append(
            await _run_probe(
                str(request.probe_url), duplicate_response.event_id, request.duplicate_count
            )
        )

    score = sum(item.points for item in scenarios)
    max_score = sum(item.max_points for item in scenarios)

    return ChaosResponse(
        provider=request.provider,
        event=request.event,
        target_url=str(request.target_url),
        score=score,
        max_score=max_score,
        grade=grade_for(score, max_score),
        scenarios=scenarios,
    )
