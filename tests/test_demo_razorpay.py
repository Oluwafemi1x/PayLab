from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

from paylab.providers.razorpay import RazorpayAdapter

_DEMO_RECEIVER = Path(__file__).resolve().parents[1] / "examples" / "demo_receiver.py"
_spec = spec_from_file_location("paylab_demo_receiver", _DEMO_RECEIVER)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load demo receiver from {_DEMO_RECEIVER}")
_demo_receiver = module_from_spec(_spec)
_spec.loader.exec_module(_demo_receiver)
client = TestClient(_demo_receiver.app)


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
