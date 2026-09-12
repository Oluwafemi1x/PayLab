import hashlib
import hmac
import secrets
import time
from typing import Any

from paylab.providers.base import BuiltEvent, ProviderAdapter
from paylab.providers.common import json_bytes


class PaystackAdapter(ProviderAdapter):
    name = "paystack"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        event_id = f"ps_{secrets.token_hex(8)}"
        reference = f"PL-{secrets.token_hex(6).upper()}"
        payload = {
            "event": event_type,
            "data": {
                "id": int(time.time() * 1000),
                "domain": "test",
                "status": "success" if "success" in event_type else "pending",
                "reference": reference,
                "amount": 500000,
                "currency": "NGN",
                "metadata": {"paylab_event_id": event_id, **metadata},
            },
        }
        body = json_bytes(payload)
        signing_secret = "invalid-secret" if invalid_signature else secret
        signature = hmac.new(signing_secret.encode(), body, hashlib.sha512).hexdigest()
        return BuiltEvent(
            event_id=event_id,
            body=body,
            headers={
                "content-type": "application/json",
                "x-paystack-signature": signature,
                "x-paylab-event-id": event_id,
            },
        )
