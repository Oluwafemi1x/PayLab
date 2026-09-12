import json

from paylab.lifecycle import DEFAULT_LIFECYCLES
from paylab.providers import BUILTIN_PROVIDERS, provider_names
from paylab.providers.monnify import MonnifyAdapter
from paylab.worker import secret_env_name


def test_monnify_is_builtin_provider() -> None:
    assert "monnify" in BUILTIN_PROVIDERS
    assert "monnify" in provider_names()
    assert isinstance(BUILTIN_PROVIDERS["monnify"], MonnifyAdapter)


def test_monnify_successful_transaction_payload_shape() -> None:
    event = MonnifyAdapter().build_event(
        "SUCCESSFUL_TRANSACTION",
        "client-secret",
        {"order_id": "ORDER-42"},
    )
    payload = json.loads(event.body)

    assert payload["eventType"] == "SUCCESSFUL_TRANSACTION"
    assert payload["eventData"]["paymentStatus"] == "PAID"
    assert payload["eventData"]["currency"] == "NGN"
    assert payload["eventData"]["paymentReference"] == event.event_id
    assert payload["eventData"]["metaData"]["paylab_event_id"] == event.event_id
    assert payload["eventData"]["metaData"]["order_id"] == "ORDER-42"
    assert event.headers["x-paylab-event-id"] == event.event_id


def test_monnify_refund_payload_shape() -> None:
    event = MonnifyAdapter().build_event("SUCCESSFUL_REFUND", "client-secret", {})
    payload = json.loads(event.body)

    assert payload["eventType"] == "SUCCESSFUL_REFUND"
    assert payload["eventData"]["refundStatus"] == "COMPLETED"
    assert payload["eventData"]["refundReference"].startswith("PL-RF-")


def test_monnify_default_lifecycle_and_worker_secret() -> None:
    assert DEFAULT_LIFECYCLES["monnify"] == (
        "SUCCESSFUL_TRANSACTION",
        "SUCCESSFUL_REFUND",
    )
    assert secret_env_name("monnify") == "PAYLAB_MONNIFY_SECRET"
