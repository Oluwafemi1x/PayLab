import json
from typing import Any


def json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize once and sign the exact bytes that will be delivered."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
