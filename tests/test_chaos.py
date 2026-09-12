from paylab.chaos import (
    evaluate_baseline,
    evaluate_duplicate,
    evaluate_invalid_signature,
    grade_for,
)
from paylab.models import DeliveryAttempt, TriggerResponse


def response(statuses: list[int]) -> TriggerResponse:
    return TriggerResponse(
        event_id="ps_test",
        provider="paystack",
        event="charge.success",
        target_url="http://127.0.0.1:9000/webhooks/paystack",
        duplicate=len(statuses),
        invalid_signature=False,
        deliveries=[
            DeliveryAttempt(attempt=index + 1, status_code=status, latency_ms=1.0)
            for index, status in enumerate(statuses)
        ],
    )


def test_baseline_passes_on_2xx() -> None:
    result = evaluate_baseline(response([200]))
    assert result.passed is True
    assert result.points == 25


def test_duplicate_requires_all_deliveries_to_succeed() -> None:
    result = evaluate_duplicate(response([200, 200, 200]), 3)
    assert result.passed is True
    assert result.points == 25


def test_invalid_signature_passes_when_rejected() -> None:
    result = evaluate_invalid_signature(response([401]))
    assert result.passed is True
    assert result.points == 25


def test_invalid_signature_fails_when_accepted() -> None:
    result = evaluate_invalid_signature(response([200]))
    assert result.passed is False
    assert result.points == 0


def test_grades() -> None:
    assert grade_for(100) == "A"
    assert grade_for(75) == "B"
    assert grade_for(50) == "C"
    assert grade_for(25) == "D"
