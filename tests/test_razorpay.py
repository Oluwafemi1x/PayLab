import json

from paylab.providers.razorpay import RazorpayAdapter


def test_razorpay_payment_captured_payload_shape() -> None:
    event = RazorpayAdapter().build_event(
        "payment.captured",
        "secret",
        {"checkout": "paylab"},
    )
    payload = json.loads(event.body)

    assert payload["entity"] == "event"
    assert payload["event"] == "payment.captured"
    assert payload["contains"] == ["payment"]
    payment = payload["payload"]["payment"]["entity"]
    assert payment["entity"] == "payment"
    assert payment["status"] == "captured"
    assert payment["captured"] is True
    assert payment["notes"]["paylab_event_id"] == event.event_id
    assert payment["notes"]["checkout"] == "paylab"


def test_razorpay_authorized_payload_is_not_marked_captured() -> None:
    event = RazorpayAdapter().build_event("payment.authorized", "secret", {})
    payment = json.loads(event.body)["payload"]["payment"]["entity"]

    assert payment["status"] == "authorized"
    assert payment["captured"] is False


def test_razorpay_refund_payload_contains_refund_and_payment() -> None:
    event = RazorpayAdapter().build_event("refund.processed", "secret", {})
    payload = json.loads(event.body)

    assert payload["contains"] == ["refund", "payment"]
    refund = payload["payload"]["refund"]["entity"]
    assert refund["entity"] == "refund"
    assert refund["status"] == "processed"
    assert refund["payment_id"] == payload["payload"]["payment"]["entity"]["id"]
