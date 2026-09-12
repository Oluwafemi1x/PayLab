# PayLab v0.5.0

> Break your payment integration before your customers do.

PayLab v0.5.0 is the first release designed for serious CI and multi-process development workflows. It keeps the local zero-config experience while adding production-oriented persistence, distributed streaming, background delivery workers, a provider plugin SDK, and broader payment-provider coverage.

## Highlights

### Five built-in payment providers

PayLab now ships with built-in adapters for:

- Paystack
- Stripe
- Flutterwave
- Monnify
- Razorpay

Each adapter generates provider-shaped webhook payloads and provider-compatible signatures for local reliability testing.

### GitHub Action reliability gate

Run PayLab directly in CI and fail a workflow when your payment webhook integration falls below a configured reliability threshold. JSON and HTML reports are generated without exposing signing secrets.

### PostgreSQL history backend

SQLite remains the zero-config default, while PostgreSQL is available for shared or longer-lived environments with native JSONB event/delivery storage and real PostgreSQL integration tests.

### Redis live streaming and workers

Redis can now back the live WebSocket/dashboard event stream across multiple processes. It also powers a background webhook-delivery queue and worker. Provider signing secrets are resolved only inside the worker process and are never stored in Redis job payloads.

### Community Provider SDK

Third-party provider adapters can be distributed as separate Python packages through the `paylab.providers` entry-point group. Plugins flow through the same trigger, chaos, history, streaming, and queued-worker paths as built-in providers.

### Reliability scenarios

PayLab can exercise duplicate delivery, invalid signatures, delayed delivery, retry recovery, timeout recovery, HTTP 5xx behavior, retry storms, lifecycle ordering, and out-of-order payment events. An optional probe can verify business-level idempotency in test environments.

## Security model

PayLab intentionally avoids persisting or streaming webhook signing secrets and raw signed request bodies. Redis job payloads do not contain provider secrets. Reliability reports contain sanitized result data only.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
paylab start
```

In a second terminal:

```powershell
uvicorn examples.demo_receiver:app --port 9000
```

Then run a reliability check:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Or test Razorpay:

```powershell
paylab trigger razorpay payment.captured http://127.0.0.1:9000/webhooks/razorpay --secret razorpay_paylab
```

## Compatibility

- Python 3.11
- Python 3.12
- Python 3.13

The release is validated by Ruff, pytest, PayLab's own GitHub Action smoke test, a real PostgreSQL service integration test, and a real Redis stream/worker integration test.

## Project status

PayLab remains alpha software. Provider payloads are representative fixtures for testing and are not a replacement for official provider sandboxes or documentation. PayLab is not affiliated with Paystack, Stripe, Flutterwave, Monnify, or Razorpay.
