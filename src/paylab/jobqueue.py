from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from paylab.models import QueuedJobStatus, QueuedTriggerRequest, TriggerResponse


class RedisJobQueue:
    """Redis-backed delivery queue. Signing secrets are never serialized into jobs."""

    def __init__(
        self,
        redis_url: str,
        *,
        queue_name: str = "paylab:jobs",
        job_ttl_seconds: int = 86400,
    ) -> None:
        if not redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("PAYLAB_REDIS_URL must use redis:// or rediss://")
        try:
            from redis import asyncio as redis_asyncio
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                'Redis workers require the optional dependency: pip install "paylab-dev[redis]"'
            ) from exc

        self.queue_name = queue_name
        self.job_ttl_seconds = job_ttl_seconds
        self._client = redis_asyncio.from_url(redis_url, decode_responses=True)

    def _job_key(self, job_id: str) -> str:
        return f"{self.queue_name}:job:{job_id}"

    async def enqueue(self, request: QueuedTriggerRequest) -> QueuedJobStatus:
        job_id = f"job_{uuid4().hex}"
        payload = request.model_dump(mode="json")
        now = datetime.now(UTC).isoformat()
        key = self._job_key(job_id)
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.hset(
                key,
                mapping={
                    "status": "queued",
                    "request": json.dumps(payload, separators=(",", ":")),
                    "created_at": now,
                    "updated_at": now,
                    "error": "",
                    "result": "",
                },
            )
            pipe.expire(key, self.job_ttl_seconds)
            pipe.rpush(self.queue_name, job_id)
            await pipe.execute()
        return QueuedJobStatus(
            job_id=job_id,
            status="queued",
            provider=request.provider,
            event=request.event,
            target_url=str(request.target_url),
        )

    async def claim(self, *, timeout_seconds: int = 5) -> tuple[str, dict[str, Any]] | None:
        item = await self._client.blpop(self.queue_name, timeout=timeout_seconds)
        if item is None:
            return None
        _, job_id = item
        raw = await self._client.hget(self._job_key(job_id), "request")
        if not raw:
            return None
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return None
        return job_id, payload

    async def mark_running(self, job_id: str) -> None:
        await self._set_status(job_id, "running")

    async def mark_succeeded(self, job_id: str, result: TriggerResponse) -> None:
        now = datetime.now(UTC).isoformat()
        await self._client.hset(
            self._job_key(job_id),
            mapping={
                "status": "succeeded",
                "updated_at": now,
                "result": result.model_dump_json(),
                "error": "",
            },
        )

    async def mark_failed(self, job_id: str, error: str) -> None:
        now = datetime.now(UTC).isoformat()
        await self._client.hset(
            self._job_key(job_id),
            mapping={"status": "failed", "updated_at": now, "error": error, "result": ""},
        )

    async def _set_status(self, job_id: str, status: str) -> None:
        await self._client.hset(
            self._job_key(job_id),
            mapping={"status": status, "updated_at": datetime.now(UTC).isoformat()},
        )

    async def get(self, job_id: str) -> QueuedJobStatus | None:
        data = await self._client.hgetall(self._job_key(job_id))
        if not data:
            return None
        request = json.loads(data["request"])
        result = TriggerResponse.model_validate_json(data["result"]) if data.get("result") else None
        return QueuedJobStatus(
            job_id=job_id,
            status=data["status"],
            provider=request["provider"],
            event=request["event"],
            target_url=request["target_url"],
            result=result,
            error=data.get("error") or None,
        )

    async def raw_job(self, job_id: str) -> dict[str, str]:
        """Internal/test helper used to verify secret-safe queue serialization."""
        return await self._client.hgetall(self._job_key(job_id))

    async def aclose(self) -> None:
        await self._client.aclose()


_job_queue: RedisJobQueue | None = None


def get_job_queue() -> RedisJobQueue:
    global _job_queue
    if _job_queue is None:
        redis_url = os.getenv("PAYLAB_REDIS_URL", "").strip()
        if not redis_url:
            raise RuntimeError("PAYLAB_REDIS_URL is required for background delivery jobs")
        queue_name = os.getenv("PAYLAB_REDIS_JOB_QUEUE", "paylab:jobs").strip() or "paylab:jobs"
        _job_queue = RedisJobQueue(redis_url, queue_name=queue_name)
    return _job_queue


def _reset_job_queue_for_tests() -> None:
    global _job_queue
    _job_queue = None
