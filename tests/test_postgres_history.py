from __future__ import annotations

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

import paylab.history as history_module
from paylab.models import DeliveryAttempt, TriggerRequest, TriggerResponse
from paylab.postgres_history import PostgresEventHistory


DATABASE_URL = os.getenv("PAYLAB_TEST_POSTGRES_URL", "")


def _request(metadata: dict[str, str]) -> TriggerRequest:
    return TriggerRequest(
        provider="paystack",
        event="charge.success",
        target_url="http://127.0.0.1:9000/webhooks/paystack",
        secret="integration-secret",
        metadata=metadata,
    )


def _response(event_id: str, *, status_code: int = 200) -> TriggerResponse:
    return TriggerResponse(
        event_id=event_id,
        provider="paystack",
        event="charge.success",
        target_url="http://127.0.0.1:9000/webhooks/paystack",
        duplicate=1,
        invalid_signature=False,
        retry_count=0,
        fault="none",
        deliveries=[
            DeliveryAttempt(
                attempt=1,
                delivery_index=1,
                retry_index=0,
                status_code=status_code,
                latency_ms=2.5,
            )
        ],
    )


@pytest.mark.skipif(not DATABASE_URL, reason="PostgreSQL integration URL is not configured")
def test_postgres_history_round_trip_and_upsert() -> None:
    store = PostgresEventHistory(DATABASE_URL)
    event_id = f"ps_pg_{uuid4().hex}"

    store.record(_request({"order_id": "ORDER-PG-1"}), _response(event_id))

    first = store.get_event(event_id)
    assert first is not None
    assert first.metadata == {"order_id": "ORDER-PG-1"}
    assert first.deliveries[0].status_code == 200

    store.record(
        _request({"order_id": "ORDER-PG-1", "state": "updated"}),
        _response(event_id, status_code=202),
    )

    updated = store.get_event(event_id)
    assert updated is not None
    assert updated.metadata["state"] == "updated"
    assert updated.deliveries[0].status_code == 202
    assert any(item.event_id == event_id for item in store.list_events(provider="paystack"))


@pytest.mark.skipif(not DATABASE_URL, reason="PostgreSQL integration URL is not configured")
def test_history_factory_selects_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYLAB_DATABASE_URL", DATABASE_URL)
    history_module._reset_history_store_for_tests()

    store = history_module.get_history_store()

    assert isinstance(store, PostgresEventHistory)
    history_module._reset_history_store_for_tests()
