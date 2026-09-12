# PayLab

[![CI](https://github.com/Oluwafemi1x/PayLab/actions/workflows/ci.yml/badge.svg)](https://github.com/Oluwafemi1x/PayLab/actions/workflows/ci.yml)
[![Action Smoke](https://github.com/Oluwafemi1x/PayLab/actions/workflows/action-smoke.yml/badge.svg)](https://github.com/Oluwafemi1x/PayLab/actions/workflows/action-smoke.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Oluwafemi1x/PayLab)](https://github.com/Oluwafemi1x/PayLab/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Break your payment integration before your customers do.**

**PayLab is an open-source payment webhook reliability and chaos-testing toolkit for CI, local development, and staging.**

Payment failures rarely happen only on the happy path. Providers retry webhooks, duplicate deliveries, deliver events late or out of order, and sometimes your endpoint times out or returns a 5xx. PayLab lets you reproduce those conditions safely before real money is involved.

With PayLab you can:

- send provider-shaped, signed webhook events;
- simulate duplicates, delays, invalid signatures, retries, timeouts, HTTP 5xx failures, and retry storms;
- test lifecycle ordering and out-of-order events;
- score webhook reliability in GitHub Actions and fail CI below a configured threshold;
- verify business-level idempotency with an optional probe;
- inspect delivery history in SQLite or PostgreSQL;
- watch sanitized delivery events live through the dashboard and WebSocket stream;
- distribute additional payment adapters through the Community Provider SDK.

> **Current release: v0.5.0 (alpha).** PayLab is intended for development, staging, CI, and reliability testing. Provider payloads are representative fixtures and are not a replacement for official provider sandboxes or documentation.

## Use PayLab in GitHub Actions

Add the PayLab reliability gate to a workflow and fail CI when your webhook integration falls below your required score:

```yaml
- name: Run PayLab reliability gate
  id: paylab
  uses: Oluwafemi1x/PayLab@v0.5.0
  with:
    provider: paystack
    event: charge.success
    target-url: http://127.0.0.1:9000/webhooks/paystack
    secret: ${{ secrets.PAYSTACK_WEBHOOK_SECRET }}
    min-score: "100"
```

The target webhook must already be reachable from the GitHub Actions runner. PayLab runs its chaos engine directly inside the Action, so the PayLab API server itself does **not** need to be started in CI.

The Action exposes:

- reliability score and maximum score;
- percentage and grade;
- pass/fail result;
- JSON report path;
- standalone HTML report path.

## What PayLab can break safely

| Scenario | What it helps you catch |
| --- | --- |
| Duplicate delivery | Missing or broken idempotency |
| Invalid signature | Signature-verification mistakes |
| Delayed webhook | Timing assumptions and fragile workflows |
| Retry recovery | Endpoints that fail once and never recover |
| Timeout recovery | Slow handlers and retry-path bugs |
| HTTP 5xx behavior | Failure handling under server errors |
| Retry storm | Duplicate side effects under repeated delivery |
| Out-of-order lifecycle | State machines that assume perfect ordering |
| Business idempotency probe | Duplicate business actions after repeated events |

## Built-in providers

PayLab v0.5.0 includes five built-in adapters:

- Paystack
- Stripe
- Flutterwave
- Monnify
- Razorpay

Third-party adapters can be installed through the [Community Provider SDK](docs/provider-sdk.md) without modifying PayLab core.

PayLab is not affiliated with Paystack, Stripe, Flutterwave, Monnify, or Razorpay.

## Quick local demo

Create a virtual environment and install PayLab:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

Start PayLab:

```powershell
paylab start
```

In a second terminal, start the bundled demo merchant:

```powershell
uvicorn examples.demo_receiver:app --port 9000
```

Then trigger a signed Paystack webhook:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Or run the checkout chaos suite:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --html paylab-report.html
```

Open:

- Dashboard: `http://127.0.0.1:8787/dashboard`
- API: `http://127.0.0.1:8787`
- Swagger: `http://127.0.0.1:8787/docs`

## v0.5.0 highlights

### GitHub Action reliability gate

PayLab can run directly in CI and fail a workflow when the tested webhook integration falls below a configured reliability threshold. JSON and HTML reports are generated from the same chaos engine used by the CLI and API.

### PostgreSQL history backend

SQLite remains PayLab's zero-config default. For shared or longer-lived environments:

```bash
pip install -e ".[dev,postgres]"
```

```text
PAYLAB_DATABASE_URL=postgresql://paylab:paylab@127.0.0.1:5432/paylab
```

PostgreSQL uses native `JSONB` for metadata and delivery attempts and exposes the same history API as SQLite.

### Redis multi-process live stream

The dashboard and `/v1/stream` WebSocket use in-process fan-out by default. For multiple PayLab processes:

```bash
pip install -e ".[dev,redis]"
```

```text
PAYLAB_REDIS_URL=redis://127.0.0.1:6379/0
PAYLAB_REDIS_CHANNEL=paylab:events
```

Processes configured with the same Redis URL and channel can publish and receive the same sanitized live delivery events. Signing secrets and raw webhook bodies are never placed on the stream.

### Redis background delivery worker

PayLab can enqueue webhook deliveries and execute them from a separate worker process. The Redis job payload does **not** contain the provider signing secret; workers resolve secrets from their own environment only when delivery runs.

```text
PAYLAB_REDIS_URL=redis://127.0.0.1:6379/0
PAYLAB_PAYSTACK_SECRET=sk_test_paylab
PAYLAB_STRIPE_WEBHOOK_SECRET=whsec_paylab
PAYLAB_FLUTTERWAVE_SECRET=flw_paylab
PAYLAB_MONNIFY_SECRET=monnify_paylab
PAYLAB_RAZORPAY_SECRET=razorpay_paylab
```

Start the API and worker separately:

```powershell
paylab start
paylab worker
```

Queue a delivery:

```http
POST /v1/jobs/trigger
Content-Type: application/json

{
  "provider": "paystack",
  "event": "charge.success",
  "target_url": "http://127.0.0.1:9000/webhooks/paystack"
}
```

The API returns `202 Accepted` with a job ID. Poll `GET /v1/jobs/{job_id}` until the job reaches `succeeded` or `failed`.

`paylab worker --once` processes at most one queued job and is useful for scripts and smoke tests.

## More examples

Trigger Razorpay:

```powershell
paylab trigger razorpay payment.captured http://127.0.0.1:9000/webhooks/razorpay --secret razorpay_paylab
```

Test lifecycle ordering:

```powershell
paylab lifecycle paystack http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
paylab lifecycle paystack http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --out-of-order
paylab lifecycle razorpay http://127.0.0.1:9000/webhooks/razorpay --secret razorpay_paylab --out-of-order
```

Run a retry storm:

```powershell
paylab storm paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --attempts 10 --interval 0.05
```

Inspect history:

```powershell
paylab history --provider paystack --limit 10
```

SQLite defaults to `~/.paylab/paylab.db`. Use `PAYLAB_DB_PATH` to change it, or configure PostgreSQL with `PAYLAB_DATABASE_URL`.

## Security model

PayLab deliberately does **not** persist or stream webhook signing secrets or raw signed webhook bodies.

Redis delivery jobs do not store provider signing secrets. Worker processes resolve secrets from environment variables only when a delivery is executed. Reports, history records, and live stream events contain sanitized delivery results.

## REST API

```text
POST /v1/events/trigger
POST /v1/jobs/trigger
GET  /v1/jobs/{job_id}
POST /v1/lifecycle
POST /v1/chaos/checkout
POST /v1/chaos/checkout/report
GET  /v1/history/events
GET  /v1/history/events/{event_id}
WS   /v1/stream
```

## Docker

Default SQLite/in-memory stream:

```bash
docker compose up --build
```

PostgreSQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

Redis live stream / job queue:

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up --build
```

PostgreSQL + Redis:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml -f docker-compose.redis.yml up --build
```

## Compatibility and validation

PayLab v0.5.0 supports Python 3.11, 3.12, and 3.13.

The release is validated with:

- Ruff;
- pytest;
- PayLab's own GitHub Action smoke test;
- a real PostgreSQL service integration test;
- a real Redis stream and worker integration test.

## Roadmap

### v0.5

- [x] GitHub Action and CI reliability gates
- [x] PostgreSQL history backend with integration tests
- [x] Redis-backed multi-process live streaming
- [x] Redis delivery job queue + worker CLI
- [x] Community Provider SDK
- [x] Additional provider adapters: Monnify and Razorpay
- [x] Stable `v0.5.0` release tag
- [ ] Launch demo assets and expanded framework examples

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

If you use PayLab against a real development or staging webhook, feedback about missing scenarios, confusing setup, provider behavior, or CI integration is especially valuable.

## License

MIT
