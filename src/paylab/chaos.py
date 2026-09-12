from __future__ import annotations

from dataclasses import dataclass

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


BASELINE = ScenarioSpec(
    name="baseline_delivery",
    description="A correctly signed payment webhook is accepted.",
    points=25,
)
DUPLICATE = ScenarioSpec(
    name="duplicate_delivery",
    description="The same event can be delivered repeatedly without transport failure.",
    points=25,
)
INVALID_SIGNATURE = ScenarioSpec(
    name="invalid_signature",
    description="A forged webhook signature is rejected.",
    points=25,
)
DELAYED = ScenarioSpec(
    name="delayed_delivery",
    description="A valid webhook is still accepted after a delivery delay.",
    points=25,
)


def _successful(delivery_status: int | None) -> bool:
    return delivery_status is not None and 200 <= delivery_status < 300


def _evidence(response: TriggerResponse) -> str:
    parts: list[str] = []
    for attempt in response.deliveries:
        if attempt.error:
            parts.append(f"attempt {attempt.attempt}: ERROR {attempt.error}")
        else:
            parts.append(
                f"attempt {attempt.attempt}: HTTP {attempt.status_code} ({attempt.latency_ms} ms)"
            )
    return "; ".join(parts)


def evaluate_baseline(response: TriggerResponse) -> ChaosScenarioResult:
    passed = bool(response.deliveries) and all(
        _successful(item.status_code) for item in response.deliveries
    )
    return ChaosScenarioResult(
        name=BASELINE.name,
        description=BASELINE.description,
        passed=passed,
        points=BASELINE.points if passed else 0,
        max_points=BASELINE.points,
        evidence=_evidence(response),
    )


def evaluate_duplicate(response: TriggerResponse, expected_deliveries: int) -> ChaosScenarioResult:
    passed = (
        len(response.deliveries) == expected_deliveries
        and expected_deliveries > 1
        and all(_successful(item.status_code) for item in response.deliveries)
    )
    return ChaosScenarioResult(
        name=DUPLICATE.name,
        description=DUPLICATE.description,
        passed=passed,
        points=DUPLICATE.points if passed else 0,
        max_points=DUPLICATE.points,
        evidence=(
            f"event_id={response.event_id}; {_evidence(response)}. "
            "Note: HTTP acknowledgement alone does not prove business-level idempotency."
        ),
    )


def evaluate_invalid_signature(response: TriggerResponse) -> ChaosScenarioResult:
    statuses = [item.status_code for item in response.deliveries if item.status_code is not None]
    passed = bool(statuses) and all(status in {400, 401, 403} for status in statuses)
    return ChaosScenarioResult(
        name=INVALID_SIGNATURE.name,
        description=INVALID_SIGNATURE.description,
        passed=passed,
        points=INVALID_SIGNATURE.points if passed else 0,
        max_points=INVALID_SIGNATURE.points,
        evidence=_evidence(response),
    )


def evaluate_delayed(response: TriggerResponse) -> ChaosScenarioResult:
    passed = bool(response.deliveries) and all(
        _successful(item.status_code) for item in response.deliveries
    )
    return ChaosScenarioResult(
        name=DELAYED.name,
        description=DELAYED.description,
        passed=passed,
        points=DELAYED.points if passed else 0,
        max_points=DELAYED.points,
        evidence=_evidence(response),
    )


def grade_for(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 50:
        return "C"
    return "D"


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
    invalid_response = await trigger_event(
        TriggerRequest(**common, invalid_signature=True)
    )
    delayed_response = await trigger_event(
        TriggerRequest(**common, delay_seconds=request.delay_seconds)
    )

    scenarios = [
        evaluate_baseline(baseline_response),
        evaluate_duplicate(duplicate_response, request.duplicate_count),
        evaluate_invalid_signature(invalid_response),
        evaluate_delayed(delayed_response),
    ]
    score = sum(item.points for item in scenarios)
    max_score = sum(item.max_points for item in scenarios)

    return ChaosResponse(
        provider=request.provider,
        event=request.event,
        target_url=str(request.target_url),
        score=score,
        max_score=max_score,
        grade=grade_for(score),
        scenarios=scenarios,
    )
