import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Any

from paylab.providers.base import BuiltEvent, ProviderAdapter
from paylab.providers.common import json_bytes


class MonnifyAdapter(ProviderAdapter):
    name = "monnify"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        event_id = f"mnfy_{secrets.token_hex(8)}"
        transaction_reference = f"MNFY|PAYLAB|{secrets.token_hex(6).upper()}"
        is_refund = event_type in {"SUCCESSFUL_REFUND", "FAILED_REFUND"}

        if is_refund:
            event_data: dict[str, Any] = {
                "refundReference": f"PL-RF-{secrets.token_hex(5).upper()}",
                "transactionReference": transaction_reference,
                "refundAmount": 1000,
                "refundStatus": "COMPLETED" if event_type == "SUCCESSFUL_REFUND" else "FAILED",
                "currency": "NGN",
                "completedOn": datetime.now(UTC).isoformat(),
                "metaData": {"paylab_event_id": event_id, **metadata},
            }
        else:
            event_data = {
                "transactionReference": transaction_reference,
                "paymentReference": event_id,
                "paidOn": datetime.now(UTC).isoformat(),
                "paymentDescription": "PayLab simulated Monnify payment",
                "amountPaid": 1000,
                "totalPayable": 1000,
                "paymentMethod": "ACCOUNT_TRANSFER",
                "currency": "NGN",
                "settlementAmount": 1000,
                "paymentStatus": "PAID" if event_type == "SUCCESSFUL_TRANSACTION" else "PENDING",
                "customer": {
                    "name": "PayLab Test Customer",
                    "email": "developer@example.com",
                },
                "metaData": {"paylab_event_id": event_id, **metadata},
            }

        payload = {"eventType": event_type, "eventData": event_data}
        body = json_bytes(payload)
        signing_secret = "invalid-secret" if invalid_signature else secret
        signature = hmac.new(signing_secret.encode(), body, hashlib.sha512).hexdigest()
        return BuiltEvent(
            event_id=event_id,
            body=body,
            headers={
                "content-type": "application/json",
                "monnify-signature": signature,
                "x-paylab-event-id": event_id,
            },
        )
