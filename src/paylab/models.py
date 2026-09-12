from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field

ProviderName = Literal["paystack", "stripe", "flutterwave"]


class TriggerRequest(BaseModel):
    provider: ProviderName
    event: str = Field(min_length=1, examples=["charge.success"])
    target_url: AnyHttpUrl
    secret: str = Field(min_length=1, description="Webhook signing secret used for the simulation.")
    duplicate: int = Field(default=1, ge=1, le=20)
    delay_seconds: float = Field(default=0.0, ge=0.0, le=60.0)
    invalid_signature: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeliveryAttempt(BaseModel):
    attempt: int
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
    deliveries: list[DeliveryAttempt]


class ChaosRequest(BaseModel):
    provider: ProviderName
    event: str = Field(min_length=1, examples=["charge.success"])
    target_url: AnyHttpUrl
    secret: str = Field(min_length=1)
    duplicate_count: int = Field(default=3, ge=2, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.0, le=10.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
