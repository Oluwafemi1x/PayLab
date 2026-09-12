import hashlib
import hmac
import secrets
import time
from typing import Any

from paylab.providers.base import BuiltEvent, ProviderAdapter
from paylab.providers.common import json_bytes


class RazorpayAdapter(ProviderAdapter):
    name = "razorpay"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        event_id = f"rzp_evt_{secrets.token_hex(8)}"
        payment_id = f"pay_{secrets.token_hex(7)}"
        order_id = f"order_{secrets.token_hex(7)}"
        created_at = int(time.time())
        is_refund = event_type.startswith("refund.")

        if is_refund or event_type == "payment.captured":
            payment_status = "captured"
        elif event_type == "payment.authorized":
            payment_status = "authorized"
        elif event_type == "payment.failed":
            payment_status = "failed"
        else:
            payment_status = "created"

        payment_entity: dict[str, Any] = {
            "id": payment_id,
            "entity": "payment",
            "amount": 70000,
            "currency": "INR",
            "status": payment_status,
            "order_id": order_id,
            "invoice_id": None,
            "international": False,
            "method": "upi",
            "amount_refunded": 10000 if is_refund else 0,
            "refund_status": "partial" if is_refund else None,
            "captured": payment_status == "captured",
            "description": "PayLab simulated Razorpay payment",
            "email": "developer@example.com",
            "contact": "+919999999999",
            "notes": {"paylab_event_id": event_id, **metadata},
            "created_at": created_at,
        }

        contains = ["payment"]
        payload: dict[str, Any] = {"payment": {"entity": payment_entity}}

        if is_refund:
            refund_id = f"rfnd_{secrets.token_hex(7)}"
            if event_type == "refund.processed":
                refund_status = "processed"
            elif event_type == "refund.failed":
                refund_status = "failed"
            else:
                refund_status = "pending"
            payload["refund"] = {
                "entity": {
                    "id": refund_id,
                    "entity": "refund",
                    "amount": 10000,
                    "currency": "INR",
                    "payment_id": payment_id,
                    "status": refund_status,
                    "notes": {"paylab_event_id": event_id, **metadata},
                    "created_at": created_at,
                }
            }
            contains = ["refund", "payment"]

        body = json_bytes(
            {
                "entity": "event",
                "account_id": "acc_PAYLABTEST0001",
                "event": event_type,
                "contains": contains,
                "payload": payload,
                "created_at": created_at,
            }
        )
        signing_secret = "invalid-secret" if invalid_signature else secret
        signature = hmac.new(signing_secret.encode(), body, hashlib.sha256).hexdigest()
        return BuiltEvent(
            event_id=event_id,
            body=body,
            headers={
                "content-type": "application/json",
                "X-Razorpay-Signature": signature,
                "x-razorpay-event-id": event_id,
                "x-paylab-event-id": event_id,
            },
        )
