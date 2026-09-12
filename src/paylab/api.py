from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from paylab import __version__
from paylab.chaos import run_checkout_chaos
from paylab.dashboard import DASHBOARD_HTML
from paylab.engine import trigger_event
from paylab.history import get_history_store
from paylab.jobqueue import get_job_queue
from paylab.lifecycle import run_lifecycle
from paylab.models import (
    ChaosRequest,
    ChaosResponse,
    HistoryEvent,
    LifecycleRequest,
    LifecycleResponse,
    ProviderName,
    QueuedJobStatus,
    QueuedTriggerRequest,
    TriggerRequest,
    TriggerResponse,
)
from paylab.providers import PROVIDERS
from paylab.reporting import render_chaos_report
from paylab.stream import get_event_stream

app = FastAPI(title="PayLab", version=__version__, description="Break your payment integration before your customers do.")


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "PayLab", "version": __version__, "message": "Break your payment integration before your customers do.", "docs": "/docs", "dashboard": "/dashboard"}


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/providers")
async def providers() -> dict[str, list[str]]:
    return {"providers": sorted(PROVIDERS.keys())}


@app.post("/v1/events/trigger", response_model=TriggerResponse)
async def trigger(request: TriggerRequest) -> TriggerResponse:
    return await trigger_event(request)


@app.post("/v1/jobs/trigger", response_model=QueuedJobStatus, status_code=202)
async def queue_trigger(request: QueuedTriggerRequest) -> QueuedJobStatus:
    try:
        return await get_job_queue().enqueue(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/v1/jobs/{job_id}", response_model=QueuedJobStatus)
async def job_status(job_id: str) -> QueuedJobStatus:
    try:
        job = await get_job_queue().get(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/v1/lifecycle", response_model=LifecycleResponse)
async def lifecycle(request: LifecycleRequest) -> LifecycleResponse:
    try:
        return await run_lifecycle(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/chaos/checkout", response_model=ChaosResponse)
async def chaos_checkout(request: ChaosRequest) -> ChaosResponse:
    return await run_checkout_chaos(request)


@app.post("/v1/chaos/checkout/report", response_class=HTMLResponse)
async def chaos_checkout_report(request: ChaosRequest) -> HTMLResponse:
    report = await run_checkout_chaos(request)
    return HTMLResponse(render_chaos_report(report))


@app.get("/v1/history/events", response_model=list[HistoryEvent])
async def history_events(limit: int = Query(default=50, ge=1, le=200), provider: ProviderName | None = None) -> list[HistoryEvent]:
    return get_history_store().list_events(limit=limit, provider=provider)


@app.get("/v1/history/events/{event_id}", response_model=HistoryEvent)
async def history_event(event_id: str) -> HistoryEvent:
    event = get_history_store().get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.websocket("/v1/stream")
async def live_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    stream = get_event_stream()
    async with stream.subscribe() as queue:
        await websocket.send_json({"type": "connected", "version": __version__})
        try:
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            return
