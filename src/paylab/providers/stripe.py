import hashlib
import hmac
import secrets
import time
from typing import Any

from paylab.providers.base import BuiltEvent, ProviderAdapter
from paylab.providers.common import json_bytes


class StripeAdapter(ProviderAdapter):
    name = "stripe"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        now = int(time.time())
        event_id = f"evt_{secrets.token_hex(12)}"
        payload = {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "created": now,
            "livemode": False,
            "data": {
                "object": {
                    "id": f"pi_{secrets.token_hex(10)}",
                    "object": "payment_intent",
                    "amount": 500000,
                    "currency": "ngn",
                    "status": "succeeded" if "succeeded" in event_type else "processing",
                    "metadata": {"paylab_event_id": event_id, **metadata},
                }
            },
        }
        body = json_bytes(payload)
        signing_secret = "invalid-secret" if invalid_signature else secret
        signed_payload = f"{now}.".encode() + body
        signature = hmac.new(
            signing_secret.encode(), signed_payload, hashlib.sha256
        ).hexdigest()
        return BuiltEvent(
            event_id=event_id,
            body=body,
            headers={
                "content-type": "application/json",
                "Stripe-Signature": f"t={now},v1={signature}",
                "x-paylab-event-id": event_id,
            },
        )
