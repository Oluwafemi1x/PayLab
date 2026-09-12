from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from paylab.engine import trigger_event
from paylab.lifecycle import lifecycle_events
from paylab.models import (
    HistoryEvent,
    LifecycleRequest,
    QueuedJobStatus,
    TriggerRequest,
)
from paylab.providers import registry
from paylab.providers.base import BuiltEvent, ProviderAdapter
from paylab.worker import secret_env_name


class AcmePayAdapter(ProviderAdapter):
    name = "acmepay"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        signature = "invalid" if invalid_signature else f"signed:{secret}"
        return BuiltEvent(
            event_id="acme_evt_1",
            body=b'{"event":"payment.succeeded"}',
            headers={
                "content-type": "application/json",
                "x-acmepay-signature": signature,
            },
        )


class FakeEntryPoint:
    name = "acmepay"

    @staticmethod
    def load() -> type[AcmePayAdapter]:
        return AcmePayAdapter


@pytest.fixture(autouse=True)
def reset_registry():
    registry._reset_provider_registry_for_tests()
    yield
    registry._reset_provider_registry_for_tests()


def _install_fake_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        registry.importlib_metadata,
        "entry_points",
        lambda **kwargs: [FakeEntryPoint()]
        if kwargs.get("group") == registry.ENTRY_POINT_GROUP
        else [],
    )


@pytest.mark.asyncio
async def test_entry_point_provider_runs_through_delivery_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_plugin(monkeypatch)

    request = TriggerRequest(
        provider="AcmePay",
        event="payment.succeeded",
        target_url="http://merchant.test/webhook",
        secret="plugin-secret",
    )

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["x-acmepay-signature"] == "signed:plugin-secret"
        return httpx.Response(200, request=http_request)

    result = await trigger_event(
        request,
        transport=httpx.MockTransport(handler),
        record_history=False,
        publish_stream=False,
    )

    assert request.provider == "acmepay"
    assert result.provider == "acmepay"
    assert result.event_id == "acme_evt_1"
    assert result.deliveries[0].status_code == 200
    assert "acmepay" in registry.provider_names()


def test_unknown_provider_is_rejected_during_execution_request_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry.importlib_metadata, "entry_points", lambda **kwargs: [])

    with pytest.raises(ValidationError, match="Unsupported provider"):
        TriggerRequest(
            provider="not-installed",
            event="payment.succeeded",
            target_url="http://merchant.test/webhook",
            secret="secret",
        )


def test_persisted_plugin_records_remain_readable_after_plugin_uninstall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry.importlib_metadata, "entry_points", lambda **kwargs: [])

    history = HistoryEvent(
        event_id="plugin_evt_1",
        provider="AcmePay",
        event="payment.succeeded",
        target_url="https://merchant.test/webhook",
        duplicate=1,
        invalid_signature=False,
        retry_count=0,
        fault="none",
        created_at=datetime.now(UTC),
        metadata={},
        deliveries=[],
    )
    job = QueuedJobStatus(
        job_id="job_1",
        status="succeeded",
        provider="AcmePay",
        event="payment.succeeded",
        target_url="https://merchant.test/webhook",
    )

    assert history.provider == "acmepay"
    assert job.provider == "acmepay"


def test_plugin_lifecycle_requires_explicit_events(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_plugin(monkeypatch)
    request = LifecycleRequest(
        provider="acmepay",
        target_url="http://merchant.test/webhook",
        secret="plugin-secret",
    )

    with pytest.raises(ValueError, match="supply events explicitly"):
        lifecycle_events(request)

    explicit = request.model_copy(update={"events": ["payment.pending", "payment.succeeded"]})
    assert lifecycle_events(explicit) == ["payment.pending", "payment.succeeded"]


def test_plugin_cannot_silently_replace_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    class ConflictingEntryPoint:
        name = "paystack"

        @staticmethod
        def load() -> type[AcmePayAdapter]:
            return AcmePayAdapter

    monkeypatch.setattr(
        registry.importlib_metadata,
        "entry_points",
        lambda **kwargs: [ConflictingEntryPoint()],
    )

    with pytest.warns(RuntimeWarning, match="already registered"):
        providers = registry.load_entry_point_providers()

    assert providers["paystack"].name == "paystack"


def test_programmatic_registration_rejects_non_adapter() -> None:
    with pytest.raises(TypeError, match="ProviderAdapter"):
        registry.register_provider(object())  # type: ignore[arg-type]


def test_programmatic_registration_name_must_match_adapter() -> None:
    with pytest.raises(ValueError, match="does not match"):
        registry.register_provider(AcmePayAdapter(), name="different-name")


def test_worker_secret_env_name_supports_builtins_and_plugins() -> None:
    assert secret_env_name("stripe") == "PAYLAB_STRIPE_WEBHOOK_SECRET"
    assert secret_env_name("razorpay") == "PAYLAB_RAZORPAY_SECRET"
    assert secret_env_name("m-pesa") == "PAYLAB_M_PESA_SECRET"
    assert secret_env_name("acme.pay") == "PAYLAB_ACME_PAY_SECRET"
