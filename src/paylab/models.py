from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, AnyHttpUrl, BaseModel, Field

FaultMode = Literal["none", "fail-once", "timeout-once"]
JobState = Literal["queued", "running", "succeeded", "failed"]


def _normalize_provider_name(value: str) -> str:
    from paylab.providers import normalize_provider_name

    return normalize_provider_name(value)


def _validate_installed_provider(value: str) -> str:
    from paylab.providers import get_provider

    provider = _normalize_provider_name(value)
    get_provider(provider)
    return provider


ProviderName = Annotated[str, AfterValidator(_normalize_provider_name)]
InstalledProviderName = Annotated[str, AfterValidator(_validate_installed_provider)]


class TriggerRequest(BaseModel):
    provider: InstalledProviderName
    event: str = Field(min_length=1, examples=["charge.success"])
    target_url: AnyHttpUrl
    secret: str = Field(min_length=1, description="Webhook signing secret used for the simulation.")
    duplicate: int = Field(default=1, ge=1, le=20)
    delay_seconds: float = Field(default=0.0, ge=0.0, le=60.0)
    invalid_signature: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: float = Field(default=0.1, ge=0.0, le=10.0)
    delivery_interval_seconds: float = Field(default=0.0, ge=0.0, le=10.0)
    timeout_seconds: float = Field(default=10.0, ge=0.05, le=60.0)
    fault: FaultMode = "none"


class QueuedTriggerRequest(BaseModel):
    """Background delivery request. Signing secrets are resolved only inside workers."""

    provider: InstalledProviderName
    event: str = Field(min_length=1, examples=["charge.success"])
    target_url: AnyHttpUrl
    duplicate: int = Field(default=1, ge=1, le=20)
    delay_seconds: float = Field(default=0.0, ge=0.0, le=60.0)
    invalid_signature: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: float = Field(default=0.1, ge=0.0, le=10.0)
    delivery_interval_seconds: float = Field(default=0.0, ge=0.0, le=10.0)
    timeout_seconds: float = Field(default=10.0, ge=0.05, le=60.0)
    fault: FaultMode = "none"


class DeliveryAttempt(BaseModel):
    attempt: int
    delivery_index: int = 1
    retry_index: int = 0
    status_code: int | None = None
    latency_ms: float | None = None
    error: str | None = None


class TriggerResponse(BaseModel):
    event_id: str
    provider: ProviderName
    event: str
    target_url: str
    duplicate: int
    invalid_signature: bool
    retry_count: int = 0
    fault: FaultMode = "none"
    deliveries: list[DeliveryAttempt]


class QueuedJobStatus(BaseModel):
    job_id: str
    status: JobState
    provider: ProviderName
    event: str
    target_url: str
    result: TriggerResponse | None = None
    error: str | None = None


class ChaosRequest(BaseModel):
    provider: InstalledProviderName
    event: str = Field(min_length=1, examples=["charge.success"])
    target_url: AnyHttpUrl
    secret: str = Field(min_length=1)
    duplicate_count: int = Field(default=3, ge=2, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.0, le=10.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    enable_fault_injection: bool = False
    retry_count: int = Field(default=2, ge=1, le=10)
    retry_delay_seconds: float = Field(default=0.05, ge=0.0, le=5.0)
    timeout_seconds: float = Field(default=0.15, ge=0.05, le=10.0)
    probe_url: AnyHttpUrl | None = None


class ChaosScenarioResult(BaseModel):
    name: str
    description: str
    passed: bool
    points: int
    max_points: int
    evidence: str


class ChaosResponse(BaseModel):
    provider: ProviderName
    event: str
    target_url: str
    score: int
    max_score: int
    grade: str
    scenarios: list[ChaosScenarioResult]


class HistoryEvent(BaseModel):
    event_id: str
    provider: ProviderName
    event: str
    target_url: str
    duplicate: int
    invalid_signature: bool
    retry_count: int
    fault: FaultMode
    created_at: datetime
    metadata: dict[str, Any]
    deliveries: list[DeliveryAttempt]


class LifecycleRequest(BaseModel):
    provider: InstalledProviderName
    target_url: AnyHttpUrl
    secret: str = Field(min_length=1)
    events: list[str] | None = Field(default=None, min_length=1, max_length=12)
    out_of_order: bool = False
    interval_seconds: float = Field(default=0.1, ge=0.0, le=10.0)
    timeout_seconds: float = Field(default=10.0, ge=0.05, le=60.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LifecycleStep(BaseModel):
    step: int
    event: str
    event_id: str
    acknowledged: bool
    status_codes: list[int | None]


class LifecycleResponse(BaseModel):
    lifecycle_id: str
    provider: ProviderName
    target_url: str
    out_of_order: bool
    steps: list[LifecycleStep]
