from fastapi import FastAPI, HTTPException, Query

from paylab import __version__
from paylab.chaos import run_checkout_chaos
from paylab.engine import trigger_event
from paylab.history import get_history_store
from paylab.models import (
    ChaosRequest,
    ChaosResponse,
    HistoryEvent,
    ProviderName,
    TriggerRequest,
    TriggerResponse,
)
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


@app.get("/v1/history/events", response_model=list[HistoryEvent])
async def history_events(
    limit: int = Query(default=50, ge=1, le=200),
    provider: ProviderName | None = None,
) -> list[HistoryEvent]:
    return get_history_store().list_events(limit=limit, provider=provider)


@app.get("/v1/history/events/{event_id}", response_model=HistoryEvent)
async def history_event(event_id: str) -> HistoryEvent:
    event = get_history_store().get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
