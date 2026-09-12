import base64
import hashlib
import hmac
import secrets
import time
from typing import Any

from paylab.providers.base import BuiltEvent, ProviderAdapter
from paylab.providers.common import json_bytes


class FlutterwaveAdapter(ProviderAdapter):
    name = "flutterwave"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        event_id = f"wbk_{secrets.token_hex(10)}"
        payload = {
            "id": event_id,
            "timestamp": int(time.time() * 1000),
            "type": event_type,
            "data": {
                "id": f"chg_{secrets.token_hex(8)}",
                "amount": 5000,
                "currency": "NGN",
                "reference": f"PL-{secrets.token_hex(6).upper()}",
                "status": "succeeded" if "completed" in event_type else "pending",
                "meta": {"paylab_event_id": event_id, **metadata},
            },
        }
        body = json_bytes(payload)
        signing_secret = "invalid-secret" if invalid_signature else secret
        digest = hmac.new(signing_secret.encode(), body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode("ascii")
        return BuiltEvent(
            event_id=event_id,
            body=body,
            headers={
                "content-type": "application/json",
                "flutterwave-signature": signature,
                "x-paylab-event-id": event_id,
            },
        )
