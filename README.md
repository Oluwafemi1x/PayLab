# PayLab

> **Break your payment integration before your customers do.**

PayLab is an open-source payment reliability and chaos-testing toolkit for developers. It
creates realistic, signed payment webhook events and deliberately injects failure conditions
so you can test your backend before production money is involved.

## v0.2.0 scope

- Paystack webhook simulation
- Stripe webhook simulation
- Flutterwave webhook simulation
- Provider-compatible webhook signatures
- Duplicate webhook delivery
- Delayed delivery
- Invalid-signature testing
- FastAPI REST API
- CLI
- Docker support
- Automated checkout chaos suite
- Reliability score + grade
- Machine-readable JSON chaos reports

> **Alpha:** Payloads are representative test fixtures and will become progressively more
> exhaustive. PayLab is not affiliated with Paystack, Stripe, or Flutterwave.

## Install locally

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
paylab start
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
paylab start
```

Open:

- API: `http://127.0.0.1:8787`
- Swagger: `http://127.0.0.1:8787/docs`


## 60-second local demo

Open **PowerShell window 1** and start PayLab:

```powershell
paylab start
```

Open **PowerShell window 2** from the same project folder and start the demo merchant:

```powershell
uvicorn examples.demo_receiver:app --port 9000
```

Open **PowerShell window 3** and deliberately send the same Paystack event three times:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --duplicate 3
```

All three deliveries use the same PayLab event ID. The demo receiver remembers that ID, making
it easy to demonstrate why real payment handlers must be idempotent.

Now test security:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --invalid-signature
```

The demo merchant should return **HTTP 401**.

## Run the checkout chaos suite

With PayLab on port `8787` and the demo merchant on port `9000`, run:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

PayLab automatically checks:

- valid signed webhook delivery
- repeated delivery of the same event
- rejection of a forged signature
- acceptance of a delayed valid event

A healthy demo receiver should score `100/100` with grade `A`. For CI or scripts, append `--json`.

> The duplicate scenario proves repeated webhook acknowledgement at the HTTP layer. It does not
> claim to prove that your internal database/order side effects are idempotent. A deeper
> idempotency probe is planned for the next milestone.

## Trigger your first webhook

Assume your application receives Paystack webhooks at:

```text
http://127.0.0.1:9000/webhooks/paystack
```

Run:

```bash
paylab trigger paystack charge.success \
  http://127.0.0.1:9000/webhooks/paystack \
  --secret sk_test_paylab
```

### Duplicate webhook test

```bash
paylab trigger paystack charge.success \
  http://127.0.0.1:9000/webhooks/paystack \
  --secret sk_test_paylab \
  --duplicate 3
```

The three requests deliberately reuse the **same event ID**. Your application should remain
idempotent and avoid creating three orders.

### Delayed event

```bash
paylab trigger stripe payment_intent.succeeded \
  http://127.0.0.1:9000/webhooks/stripe \
  --secret whsec_paylab \
  --delay 5
```

### Bad signature

```bash
paylab trigger flutterwave charge.completed \
  http://127.0.0.1:9000/webhooks/flutterwave \
  --secret flw_paylab \
  --invalid-signature
```

Your backend should reject the event.

## REST API

```http
POST /v1/events/trigger
Content-Type: application/json
```

```json
{
  "provider": "paystack",
  "event": "charge.success",
  "target_url": "http://127.0.0.1:9000/webhooks/paystack",
  "secret": "sk_test_paylab",
  "duplicate": 3,
  "delay_seconds": 0,
  "invalid_signature": false,
  "metadata": {
    "order_id": "ORDER-1001"
  }
}
```

## Why PayLab?

Payment bugs often appear in failure paths:

- The provider sends the same event twice.
- A webhook arrives late.
- A signature is invalid.
- Your endpoint returns 500.
- Events arrive out of order.
- A retry happens after your database already committed an order.

PayLab's goal is to make those scenarios reproducible in local development and CI.

## Roadmap

### v0.3
- Persistent event history
- Retry policies and retry storms
- Timeout / HTTP 500 injection
- Business-level idempotency probe
- Out-of-order lifecycle scenarios

### v0.4
- PostgreSQL + Redis workers
- Web dashboard
- WebSocket live event stream
- HTML reliability reports

### v0.5
- GitHub Action
- CI failure gates
- Community provider SDK

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

## License

MIT
