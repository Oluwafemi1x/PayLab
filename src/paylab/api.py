from fastapi import FastAPI

from paylab import __version__
from paylab.chaos import run_checkout_chaos
from paylab.engine import trigger_event
from paylab.models import ChaosRequest, ChaosResponse, TriggerRequest, TriggerResponse
from paylab.providers import PROVIDERS

app = FastAPI(
    title="PayLab",
    version=__version__,
    description="Break your payment integration before your customers do.",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "PayLab",
        "version": __version__,
        "message": "Break your payment integration before your customers do.",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/providers")
async def providers() -> dict[str, list[str]]:
    return {"providers": sorted(PROVIDERS.keys())}


@app.post("/v1/events/trigger", response_model=TriggerResponse)
async def trigger(request: TriggerRequest) -> TriggerResponse:
    return await trigger_event(request)


@app.post("/v1/chaos/checkout", response_model=ChaosResponse)
async def chaos_checkout(request: ChaosRequest) -> ChaosResponse:
    return await run_checkout_chaos(request)
