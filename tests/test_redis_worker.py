from __future__ import annotations

import os
import subprocess
import sys
from uuid import uuid4

import pytest

from paylab.jobqueue import RedisJobQueue
from paylab.models import QueuedTriggerRequest
from paylab.worker import secret_env_name

pytest.importorskip("redis")

REDIS_URL = os.getenv("PAYLAB_TEST_REDIS_URL", "")


def test_provider_secret_environment_names_match_public_config() -> None:
    assert secret_env_name("paystack") == "PAYLAB_PAYSTACK_SECRET"
    assert secret_env_name("stripe") == "PAYLAB_STRIPE_WEBHOOK_SECRET"
    assert secret_env_name("flutterwave") == "PAYLAB_FLUTTERWAVE_SECRET"
    assert secret_env_name("monnify") == "PAYLAB_MONNIFY_SECRET"
    assert secret_env_name("razorpay") == "PAYLAB_RAZORPAY_SECRET"


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Redis integration URL is not configured")
async def test_worker_delivers_from_separate_process_without_queueing_secret(tmp_path) -> None:
    queue_name = f"paylab:test:jobs:{uuid4().hex}"
    queue = RedisJobQueue(REDIS_URL, queue_name=queue_name)
    secret = "sk_test_paylab"

    try:
        queued = await queue.enqueue(
            QueuedTriggerRequest(
                provider="paystack",
                event="charge.success",
                target_url="http://127.0.0.1:9000/webhooks/paystack",
            )
        )
        raw_before = await queue.raw_job(queued.job_id)
        assert secret not in str(raw_before)
        assert "secret" not in raw_before.get("request", "")

        env = os.environ.copy()
        env["PAYLAB_REDIS_URL"] = REDIS_URL
        env["PAYLAB_REDIS_JOB_QUEUE"] = queue_name
        env["PAYLAB_PAYSTACK_SECRET"] = secret
        env["PAYLAB_DB_PATH"] = str(tmp_path / "worker.db")

        code = (
            "import asyncio\n"
            "from paylab.worker import run_worker\n"
            "asyncio.run(run_worker(once=True, poll_timeout_seconds=2))\n"
        )
        await __import__("asyncio").to_thread(
            subprocess.run,
            [sys.executable, "-c", code],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        completed = await queue.get(queued.job_id)
        raw_after = await queue.raw_job(queued.job_id)
    finally:
        await queue.aclose()

    assert completed is not None
    assert completed.status == "succeeded"
    assert completed.result is not None
    assert completed.result.deliveries[0].status_code == 200
    assert secret not in str(raw_after)


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Redis integration URL is not configured")
async def test_worker_marks_missing_provider_secret_as_failed(monkeypatch) -> None:
    from paylab.worker import process_one

    queue_name = f"paylab:test:jobs:{uuid4().hex}"
    queue = RedisJobQueue(REDIS_URL, queue_name=queue_name)
    monkeypatch.delenv("PAYLAB_PAYSTACK_SECRET", raising=False)

    try:
        queued = await queue.enqueue(
            QueuedTriggerRequest(
                provider="paystack",
                event="charge.success",
                target_url="http://127.0.0.1:9000/webhooks/paystack",
            )
        )
        assert await process_one(queue, timeout_seconds=1)
        failed = await queue.get(queued.job_id)
    finally:
        await queue.aclose()

    assert failed is not None
    assert failed.status == "failed"
    assert failed.error == "Worker secret is not configured: PAYLAB_PAYSTACK_SECRET"
