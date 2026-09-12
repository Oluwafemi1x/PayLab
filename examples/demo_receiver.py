"""Tiny merchant webhook receiver used to demo PayLab locally."""

import base64
import hashlib
import hmac
import os

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="PayLab Demo Merchant")

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET", "sk_test_paylab")
STRIPE_SECRET = os.getenv("STRIPE_SECRET", "whsec_paylab")
FLUTTERWAVE_SECRET = os.getenv("FLUTTERWAVE_SECRET", "flw_paylab")

seen_event_ids: set[str] = set()


def remember(event_id: str | None) -> bool:
    if not event_id:
        return False
    duplicate = event_id in seen_event_ids
    seen_event_ids.add(event_id)
    return duplicate


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "demo merchant listening"}


@app.post("/webhooks/paystack")
async def paystack_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(PAYSTACK_SECRET.encode(), body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Paystack signature")
    event_id = request.headers.get("x-paylab-event-id")
    return {"accepted": True, "duplicate": remember(event_id), "event_id": event_id}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature_header = request.headers.get("stripe-signature", "")
    parts = dict(
        item.split("=", 1) for item in signature_header.split(",") if "=" in item
    )
    timestamp = parts.get("t", "")
    signature = parts.get("v1", "")
    expected = hmac.new(
        STRIPE_SECRET.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    if not timestamp or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Stripe signature")
    event_id = request.headers.get("x-paylab-event-id")
    return {"accepted": True, "duplicate": remember(event_id), "event_id": event_id}


@app.post("/webhooks/flutterwave")
async def flutterwave_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature = request.headers.get("flutterwave-signature", "")
    digest = hmac.new(FLUTTERWAVE_SECRET.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Flutterwave signature")
    event_id = request.headers.get("x-paylab-event-id")
    return {"accepted": True, "duplicate": remember(event_id), "event_id": event_id}
