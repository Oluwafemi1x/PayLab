from pathlib import Path

import httpx
import pytest

from paylab.history import EventHistory
from paylab.lifecycle import run_lifecycle
from paylab.models import LifecycleRequest
from paylab.stream import EventStream


@pytest.mark.asyncio
async def test_lifecycle_uses_default_sequence(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)

    result = await run_lifecycle(
        LifecycleRequest(provider="paystack", target_url="http://merchant.test/webhook", secret="secret", interval_seconds=0),
        history=EventHistory(tmp_path / "history.db"),
        stream=EventStream(),
        transport=httpx.MockTransport(handler),
    )
    assert [step.event for step in result.steps] == ["charge.success", "refund.processed"]
    assert all(step.acknowledged for step in result.steps)


@pytest.mark.asyncio
async def test_lifecycle_can_reverse_order(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)

    result = await run_lifecycle(
        LifecycleRequest(provider="stripe", target_url="http://merchant.test/webhook", secret="secret", events=["a", "b", "c"], out_of_order=True, interval_seconds=0),
        history=EventHistory(tmp_path / "history.db"),
        stream=EventStream(),
        transport=httpx.MockTransport(handler),
    )
    assert [step.event for step in result.steps] == ["c", "b", "a"]
