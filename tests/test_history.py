from pathlib import Path

from paylab.history import EventHistory
from paylab.models import DeliveryAttempt, TriggerRequest, TriggerResponse


def test_history_round_trip(tmp_path: Path) -> None:
    store = EventHistory(tmp_path / "history.db")
    request = TriggerRequest(
        provider="paystack",
        event="charge.success",
        target_url="http://127.0.0.1:9000/webhooks/paystack",
        secret="secret",
        metadata={"order_id": "ORDER-1"},
    )
    response = TriggerResponse(
        event_id="ps_test",
        provider="paystack",
        event="charge.success",
        target_url=str(request.target_url),
        duplicate=1,
        invalid_signature=False,
        retry_count=0,
        fault="none",
        deliveries=[
            DeliveryAttempt(
                attempt=1,
                delivery_index=1,
                retry_index=0,
                status_code=200,
                latency_ms=1.5,
            )
        ],
    )

    store.record(request, response)

    item = store.get_event("ps_test")
    assert item is not None
    assert item.metadata == {"order_id": "ORDER-1"}
    assert item.deliveries[0].status_code == 200
    assert store.list_events(provider="paystack")[0].event_id == "ps_test"
