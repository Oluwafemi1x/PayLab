from fastapi.testclient import TestClient

import paylab
from paylab.api import app

client = TestClient(app)


def test_dashboard_is_served() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "PayLab Live" in response.text
    assert "/v1/stream" in response.text


def test_openapi_contains_v04_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/lifecycle" in paths
    assert "/v1/chaos/checkout/report" in paths


def test_websocket_connects() -> None:
    with client.websocket_connect("/v1/stream") as websocket:
        payload = websocket.receive_json()
        assert payload == {"type": "connected", "version": paylab.__version__}
