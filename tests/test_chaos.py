from paylab.chaos import (
    evaluate_baseline,
    evaluate_duplicate,
    evaluate_idempotency_probe,
    evaluate_invalid_signature,
    evaluate_retry_after_500,
    evaluate_timeout_recovery,
    grade_for,
)
from paylab.models import DeliveryAttempt, TriggerResponse


def response(statuses: list[int | None], errors: list[str | None] | None = None) -> TriggerResponse:
    errors = errors or [None] * len(statuses)
    return TriggerResponse(
        event_id="ps_test",
        provider="paystack",
        event="charge.success",
        target_url="http://127.0.0.1:9000/webhooks/paystack",
        duplicate=1,
        invalid_signature=False,
        retry_count=max(0, len(statuses) - 1),
        fault="none",
        deliveries=[
            DeliveryAttempt(
                attempt=index + 1,
                delivery_index=1,
                retry_index=index,
                status_code=status,
                latency_ms=1.0,
                error=errors[index],
            )
            for index, status in enumerate(statuses)
        ],
    )


def test_baseline_passes_on_2xx() -> None:
    result = evaluate_baseline(response([200]))
    assert result.passed is True
    assert result.points == 25


def test_duplicate_requires_each_delivery_index() -> None:
    item = response([200, 200, 200])
    for index, delivery in enumerate(item.deliveries, start=1):
        delivery.delivery_index = index
        delivery.retry_index = 0
    item.duplicate = 3
    result = evaluate_duplicate(item, 3)
    assert result.passed is True


def test_invalid_signature_passes_when_rejected() -> None:
    assert evaluate_invalid_signature(response([401])).passed is True


def test_invalid_signature_fails_when_accepted() -> None:
    assert evaluate_invalid_signature(response([200])).passed is False


def test_retry_after_500_requires_recovery() -> None:
    assert evaluate_retry_after_500(response([500, 200])).passed is True


def test_timeout_recovery_requires_error_then_success() -> None:
    result = evaluate_timeout_recovery(response([None, 200], ["timed out", None]))
    assert result.passed is True


def test_idempotency_probe_requires_one_side_effect() -> None:
    result = evaluate_idempotency_probe(
        event_id="ps_test",
        expected_deliveries=3,
        payload={"deliveries_received": 3, "side_effect_count": 1},
    )
    assert result.passed is True


def test_grades_use_percentage() -> None:
    assert grade_for(175, 175) == "A"
    assert grade_for(75, 100) == "B"
    assert grade_for(50, 100) == "C"
    assert grade_for(25, 100) == "D"
