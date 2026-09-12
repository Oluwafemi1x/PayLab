from __future__ import annotations

import asyncio
import os

from paylab.engine import trigger_event
from paylab.jobqueue import RedisJobQueue, get_job_queue
from paylab.models import ProviderName, QueuedTriggerRequest, TriggerRequest

_SECRET_ENV_NAMES: dict[ProviderName, str] = {
    "paystack": "PAYLAB_PAYSTACK_SECRET",
    "stripe": "PAYLAB_STRIPE_WEBHOOK_SECRET",
    "flutterwave": "PAYLAB_FLUTTERWAVE_SECRET",
}


def secret_env_name(provider: ProviderName) -> str:
    return _SECRET_ENV_NAMES[provider]


def resolve_provider_secret(provider: ProviderName) -> str:
    name = secret_env_name(provider)
    secret = os.getenv(name, "")
    if not secret:
        raise RuntimeError(f"Worker secret is not configured: {name}")
    return secret


def _safe_failure(exc: RuntimeError | ValueError) -> str:
    if isinstance(exc, RuntimeError) and str(exc).startswith("Worker secret is not configured:"):
        return str(exc)
    return f"{type(exc).__name__}: worker execution failed"


async def process_one(queue: RedisJobQueue | None = None, *, timeout_seconds: int = 5) -> bool:
    queue = queue or get_job_queue()
    claimed = await queue.claim(timeout_seconds=timeout_seconds)
    if claimed is None:
        return False

    job_id, payload = claimed
    await queue.mark_running(job_id)
    try:
        queued = QueuedTriggerRequest.model_validate(payload)
        secret = resolve_provider_secret(queued.provider)
        request = TriggerRequest(secret=secret, **queued.model_dump(mode="python"))
        result = await trigger_event(request)
        await queue.mark_succeeded(job_id, result)
    except (RuntimeError, ValueError) as exc:
        await queue.mark_failed(job_id, _safe_failure(exc))
    return True


async def run_worker(*, once: bool = False, poll_timeout_seconds: int = 5) -> None:
    queue = get_job_queue()
    try:
        while True:
            processed = await process_one(queue, timeout_seconds=poll_timeout_seconds)
            if once:
                return
            if not processed:
                await asyncio.sleep(0)
    finally:
        await queue.aclose()
