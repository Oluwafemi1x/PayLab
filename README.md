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

## v0.5 preview

### GitHub Action reliability gate

PayLab can run directly inside GitHub Actions and fail a workflow when a webhook integration falls below a configured reliability threshold. The Action runs the chaos engine directly, so you do **not** need to start the PayLab API server in CI.

Your application or staging webhook endpoint must already be reachable from the GitHub Actions runner.

```yaml
name: Payment reliability

on:
  pull_request:

jobs:
  paylab:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Start your application here so its webhook endpoint is reachable.
      - name: Start application
        run: ./scripts/start-test-app.sh

      - name: Run PayLab reliability gate
        id: paylab
        uses: Oluwafemi1x/PayLab@main
        with:
          provider: paystack
          event: charge.success
          target-url: http://127.0.0.1:9000/webhooks/paystack
          secret: ${{ secrets.PAYSTACK_WEBHOOK_SECRET }}
          min-score: "100"

      - name: Show score
        run: echo "PayLab score = ${{ steps.paylab.outputs.percentage }}%"
```

The Action generates both `paylab-report.json` and `paylab-report.html` by default and exposes score, grade, percentage, pass/fail, and report-path outputs.

Use `deep: "true"` only against local or staging endpoints that intentionally support PayLab's test-only fault protocol.

`@main` is the preview channel while v0.5 is under development. A stable `v0.5.0` tag will be published after the full v0.5 milestone passes its release checks.

### PostgreSQL history backend

SQLite remains PayLab's zero-config default. For shared or longer-lived environments, install the optional PostgreSQL backend:

```bash
pip install -e ".[dev,postgres]"
```

Set a PostgreSQL URL before starting PayLab:

```text
PAYLAB_DATABASE_URL=postgresql://paylab:paylab@127.0.0.1:5432/paylab
```

`PAYLAB_DATABASE_URL` takes precedence over `PAYLAB_DB_PATH`. PostgreSQL stores event metadata and delivery attempts as `JSONB`, and uses the same history API as SQLite.

Run PayLab plus PostgreSQL with Docker Compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

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

By default, PayLab stores history in SQLite at `~/.paylab/paylab.db`. Override that path with `PAYLAB_DB_PATH`, or configure PostgreSQL with `PAYLAB_DATABASE_URL`.

```powershell
paylab history --provider paystack --limit 10
```

PayLab deliberately does **not** persist webhook signing secrets or raw signed webhook bodies. This rule applies to both SQLite and PostgreSQL. Live WebSocket messages follow the same rule.

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

SQLite/default:

```bash
docker compose up --build
```

PostgreSQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

## Roadmap

### v0.5

- [x] GitHub Action and CI reliability gates
- [x] PostgreSQL history backend with integration tests
- [ ] Redis-backed multi-process event streaming/workers
- [ ] Community provider SDK
- [ ] Additional provider adapters
- [ ] Stable `v0.5.0` release tag and launch assets

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

PostgreSQL integration development:

```bash
pip install -e ".[dev,postgres]"
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
