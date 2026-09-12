from fastapi.testclient import TestClient

from examples.demo_receiver import app
from paylab.providers.razorpay import RazorpayAdapter

client = TestClient(app)


def test_demo_receiver_accepts_valid_razorpay_signature() -> None:
    event = RazorpayAdapter().build_event("payment.captured", "razorpay_paylab", {})
    response = client.post(
        "/webhooks/razorpay",
        content=event.body,
        headers=event.headers,
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["event_id"] == event.event_id


def test_demo_receiver_rejects_invalid_razorpay_signature() -> None:
    event = RazorpayAdapter().build_event(
        "payment.captured",
        "razorpay_paylab",
        {},
        invalid_signature=True,
    )
    response = client.post(
        "/webhooks/razorpay",
        content=event.body,
        headers=event.headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Razorpay signature"
