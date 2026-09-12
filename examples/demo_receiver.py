"""Tiny merchant webhook receiver used to demo PayLab locally."""

import asyncio
import base64
import hashlib
import hmac
import os
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="PayLab Demo Merchant")

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET", "sk_test_paylab")
STRIPE_SECRET = os.getenv("STRIPE_SECRET", "whsec_paylab")
FLUTTERWAVE_SECRET = os.getenv("FLUTTERWAVE_SECRET", "flw_paylab")

received_counts: defaultdict[str, int] = defaultdict(int)
side_effect_counts: defaultdict[str, int] = defaultdict(int)
failure_once_seen: set[str] = set()
timeout_once_seen: set[str] = set()


def record_business_effect(event_id: str | None) -> bool:
    if not event_id:
        return False
    received_counts[event_id] += 1
    duplicate = side_effect_counts[event_id] > 0
    if not duplicate:
        side_effect_counts[event_id] += 1
    return duplicate


async def apply_fault(request: Request, event_id: str | None) -> bool:
    if not event_id:
        return False
    fault = request.headers.get("x-paylab-fault", "none")
    if fault == "fail-once" and event_id not in failure_once_seen:
        failure_once_seen.add(event_id)
        raise HTTPException(status_code=500, detail="PayLab fail-once fault")
    if fault == "timeout-once" and event_id not in timeout_once_seen:
        timeout_once_seen.add(event_id)
        record_business_effect(event_id)
        delay = float(request.headers.get("x-paylab-fault-delay", "0.5"))
        await asyncio.sleep(delay)
        return True
    return False


def _accepted(event_id: str | None) -> dict[str, object]:
    return {
        "accepted": True,
        "duplicate": record_business_effect(event_id),
        "event_id": event_id,
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "demo merchant listening"}


@app.get("/paylab/probe")
async def paylab_probe(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "deliveries_received": received_counts[event_id],
        "side_effect_count": side_effect_counts[event_id],
    }


@app.post("/webhooks/paystack")
async def paystack_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(PAYSTACK_SECRET.encode(), body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Paystack signature")
    event_id = request.headers.get("x-paylab-event-id")
    already_recorded = await apply_fault(request, event_id)
    if already_recorded:
        return {"accepted": True, "duplicate": False, "event_id": event_id}
    return _accepted(event_id)


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature_header = request.headers.get("stripe-signature", "")
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = parts.get("t", "")
    signature = parts.get("v1", "")
    expected = hmac.new(
        STRIPE_SECRET.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    if not timestamp or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Stripe signature")
    event_id = request.headers.get("x-paylab-event-id")
    already_recorded = await apply_fault(request, event_id)
    if already_recorded:
        return {"accepted": True, "duplicate": False, "event_id": event_id}
    return _accepted(event_id)


@app.post("/webhooks/flutterwave")
async def flutterwave_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature = request.headers.get("flutterwave-signature", "")
    digest = hmac.new(FLUTTERWAVE_SECRET.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Flutterwave signature")
    event_id = request.headers.get("x-paylab-event-id")
    already_recorded = await apply_fault(request, event_id)
    if already_recorded:
        return {"accepted": True, "duplicate": False, "event_id": event_id}
    return _accepted(event_id)
