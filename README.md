# PayLab

> **Break your payment integration before your customers do.**

PayLab is an open-source payment reliability and chaos-testing toolkit for developers. It creates realistic signed payment webhook events, repeats and delays them, injects controlled failures, retries failed deliveries, records what happened, and exposes a live dashboard for watching tests as they happen.

## v0.4.0

- Paystack, Stripe, and Flutterwave webhook simulation
- Provider-compatible webhook signatures
- Duplicate, delayed, and invalid-signature delivery tests
- Retry-on-timeout and retry-on-HTTP-5xx behavior
- Rapid repeated-delivery storms
- Persistent SQLite event history
- Deep fail-once and timeout-once chaos tests
- Optional business-level idempotency probe
- **Live browser dashboard**
- **WebSocket delivery stream**
- **Payment lifecycle and out-of-order event simulation**
- **Standalone HTML reliability reports**
- FastAPI REST API, CLI, Docker, pytest, and GitHub Actions

> **Alpha:** Payloads are representative test fixtures. PayLab is not affiliated with Paystack, Stripe, or Flutterwave.

## Install

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

- Dashboard: `http://127.0.0.1:8787/dashboard`
- API: `http://127.0.0.1:8787`
- Swagger: `http://127.0.0.1:8787/docs`

## Quick demo

Start PayLab, then run the bundled demo merchant in a second terminal:

```powershell
paylab start
uvicorn examples.demo_receiver:app --port 9000
```

Trigger a signed event:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Open `/dashboard` and watch deliveries appear live.

## Lifecycle testing

```powershell
paylab lifecycle paystack http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Reverse the sequence to simulate out-of-order events:

```powershell
paylab lifecycle paystack http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --out-of-order
```

Use a custom sequence:

```powershell
paylab lifecycle stripe http://127.0.0.1:9000/webhooks/stripe --secret whsec_paylab --events "payment_intent.succeeded,charge.refunded"
```

## Checkout chaos suite

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Generate a standalone HTML report:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --html paylab-report.html
```

Deep mode adds controlled HTTP 500 and timeout recovery checks:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --deep --probe-url http://127.0.0.1:9000/paylab/probe
```

> **Security:** Deep fault controls are for local/staging test endpoints only.

## Retry storms

```powershell
paylab storm paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --attempts 10 --interval 0.05
```

## Persistent history

By default, PayLab stores history at `~/.paylab/paylab.db`. Override with `PAYLAB_DB_PATH`.

```powershell
paylab history --provider paystack --limit 10
```

PayLab deliberately does **not** persist webhook signing secrets or raw signed webhook bodies. Live WebSocket messages follow the same rule.

## REST API

```text
POST /v1/events/trigger
POST /v1/lifecycle
POST /v1/chaos/checkout
POST /v1/chaos/checkout/report
GET  /v1/history/events
GET  /v1/history/events/{event_id}
WS   /v1/stream
```

## Docker

```bash
docker compose up --build
```

## Roadmap

### v0.5

- PostgreSQL history backend with integration tests
- Redis-backed multi-process event streaming/workers
- GitHub Action and CI reliability gates
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
