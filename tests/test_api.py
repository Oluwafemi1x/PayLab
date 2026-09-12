from pathlib import Path

from fastapi.testclient import TestClient

import paylab.api as api_module
from paylab.api import app
from paylab.history import EventHistory

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_provider_list() -> None:
    response = client.get("/v1/providers")
    assert response.status_code == 200
    assert response.json()["providers"] == ["flutterwave", "monnify", "paystack", "stripe"]


def test_openapi_contains_v03_routes() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/chaos/checkout" in paths
    assert "/v1/history/events" in paths
    assert "/v1/history/events/{event_id}" in paths


def test_history_returns_empty_list(tmp_path: Path, monkeypatch) -> None:
    store = EventHistory(tmp_path / "api-history.db")
    monkeypatch.setattr(api_module, "get_history_store", lambda: store)
    response = client.get("/v1/history/events")
    assert response.status_code == 200
    assert response.json() == []
