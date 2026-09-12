from fastapi.testclient import TestClient

from paylab.api import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_provider_list() -> None:
    response = client.get("/v1/providers")
    assert response.status_code == 200
    assert response.json()["providers"] == ["flutterwave", "paystack", "stripe"]


def test_openapi_contains_chaos_checkout() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/v1/chaos/checkout" in response.json()["paths"]
