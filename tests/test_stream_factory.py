import pytest

import paylab.stream as stream_module
from paylab.stream import EventStream


def test_stream_factory_uses_memory_without_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PAYLAB_REDIS_URL", raising=False)
    stream_module._reset_event_stream_for_tests()

    stream = stream_module.get_event_stream()

    assert isinstance(stream, EventStream)
    stream_module._reset_event_stream_for_tests()


def test_redis_stream_rejects_unsupported_url() -> None:
    with pytest.raises(ValueError, match="redis://"):
        stream_module.RedisEventStream("http://localhost:6379")
