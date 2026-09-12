# PayLab

> **Break your payment integration before your customers do.**

PayLab is an open-source payment reliability and chaos-testing toolkit for developers. It
creates realistic signed payment webhook events, repeats them, delays them, injects controlled
failures, retries failed deliveries, and records what happened so backend teams can test failure
paths before production money is involved.

## v0.3.0 scope

- Paystack, Stripe, and Flutterwave webhook simulation
- Provider-compatible webhook signatures
- Duplicate and delayed webhook delivery
- Invalid-signature testing
- Retry-on-timeout and retry-on-HTTP-5xx behavior
- Rapid repeated-delivery storms with one event ID
- Persistent SQLite event history
- Opt-in fail-once and timeout-once fault injection
- Optional business-level idempotency probe
- FastAPI REST API + CLI
- Docker support with persistent history volume
- JSON chaos reports for automation

> **Alpha:** Payloads are representative test fixtures and will become progressively more
> exhaustive. PayLab is not affiliated with Paystack, Stripe, or Flutterwave.

## Install locally

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
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

Open terminal 1 and start PayLab:

```powershell
paylab start
```

Open terminal 2 and start the bundled demo merchant:

```powershell
uvicorn examples.demo_receiver:app --port 9000
```

Open terminal 3 and trigger a signed Paystack-style webhook:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Send the same event three times:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --duplicate 3
```

Test signature validation:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --invalid-signature
```

The demo merchant should reject that request with HTTP `401`.

## Standard checkout chaos suite

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

The standard suite checks:

- valid signed delivery
- duplicate delivery
- invalid-signature rejection
- delayed delivery

A healthy receiver scores `100/100` with grade `A`.

## Deep chaos mode

The bundled demo receiver supports a **test-only PayLab fault protocol**. Run:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --deep --probe-url http://127.0.0.1:9000/paylab/probe
```

Deep mode adds:

- initial HTTP `500` followed by automatic retry and recovery
- delivery timeout followed by automatic retry and recovery
- business-level idempotency verification through the probe endpoint

The probe checks that repeated delivery of one event produced exactly one business side effect.

> **Security:** `--deep` sends PayLab-specific fault headers. Use it only against local/staging
> endpoints designed to understand them. Never expose test fault controls on a production
> webhook endpoint.

## Retry storms

Send one event repeatedly in quick succession:

```powershell
paylab storm paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --attempts 10 --interval 0.05
```

Every delivery shares the same PayLab event ID, which makes this useful for stress-testing
idempotency and duplicate handling.

## Automatic retries

PayLab can retry transport failures and HTTP `5xx` responses:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --retry 3 --retry-delay 0.1 --timeout 2
```

HTTP `4xx` responses are treated as deliberate rejections and are not retried by this command.

## Persistent event history

PayLab stores simulation history in SQLite. By default:

```text
~/.paylab/paylab.db
```

Override it with:

```text
PAYLAB_DB_PATH=/your/path/paylab.db
```

Show recent events:

```powershell
paylab history
```

Filter by provider:

```powershell
paylab history --provider paystack --limit 10
```

PayLab does **not** persist webhook signing secrets or raw signed webhook bodies.

## REST API

### Trigger an event

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
  "duplicate": 1,
  "retry_count": 2,
  "retry_delay_seconds": 0.1,
  "timeout_seconds": 5,
  "invalid_signature": false,
  "metadata": {
    "order_id": "ORDER-1001"
  }
}
```

### History

```http
GET /v1/history/events?limit=20&provider=paystack
GET /v1/history/events/{event_id}
```

### Chaos suite

```http
POST /v1/chaos/checkout
```

For CI or scripts, the CLI supports:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --json
```

## Docker

```bash
docker compose up --build
```

Docker Compose mounts a named volume for the SQLite history database so event history survives
container recreation.

## Why PayLab?

Payment bugs often appear in failure paths:

- a provider sends the same event twice
- a webhook arrives late
- a signature is invalid
- an endpoint returns `500`
- a request times out after the database already committed
- the provider retries and creates a duplicate order

PayLab's goal is to make these scenarios reproducible in local development and CI.

## Roadmap

### v0.4

- PostgreSQL + Redis workers
- Web dashboard
- WebSocket live event stream
- HTML reliability reports
- Out-of-order payment lifecycle scenarios

### v0.5

- GitHub Action
- CI reliability gates
- Community provider SDK
- Additional provider adapters

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
