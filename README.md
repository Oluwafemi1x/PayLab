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
- name: Run PayLab reliability gate
  id: paylab
  uses: Oluwafemi1x/PayLab@main
  with:
    provider: paystack
    event: charge.success
    target-url: http://127.0.0.1:9000/webhooks/paystack
    secret: ${{ secrets.PAYSTACK_WEBHOOK_SECRET }}
    min-score: "100"
```

The Action generates JSON and HTML reports and exposes score, grade, percentage, pass/fail, and report-path outputs.

### PostgreSQL history backend

SQLite remains PayLab's zero-config default. For shared or longer-lived environments:

```bash
pip install -e ".[dev,postgres]"
```

```text
PAYLAB_DATABASE_URL=postgresql://paylab:paylab@127.0.0.1:5432/paylab
```

PostgreSQL uses native `JSONB` for metadata and delivery attempts and the same history API as SQLite.

### Redis multi-process live stream

The live dashboard and `/v1/stream` WebSocket use an in-process event fan-out by default. For multiple PayLab API processes, install Redis support:

```bash
pip install -e ".[dev,redis]"
```

```text
PAYLAB_REDIS_URL=redis://127.0.0.1:6379/0
PAYLAB_REDIS_CHANNEL=paylab:events
```

All processes configured with the same Redis URL/channel can publish and receive the same sanitized live delivery events. Signing secrets and raw webhook bodies are never placed on the stream.

### Redis background delivery worker

PayLab can also enqueue webhook deliveries and let a separate worker process execute them. The API queue payload does **not** accept or store the provider signing secret. Workers resolve secrets only from their own environment.

```text
PAYLAB_REDIS_URL=redis://127.0.0.1:6379/0
PAYLAB_PAYSTACK_SECRET=sk_test_paylab
PAYLAB_STRIPE_SECRET=whsec_paylab
PAYLAB_FLUTTERWAVE_SECRET=flw_paylab
```

Start the API and worker in separate terminals:

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

The API returns `202 Accepted` with a job ID. Poll `GET /v1/jobs/{job_id}` until the job reaches `succeeded` or `failed`. Completed delivery results contain status codes and latencies but never the signing secret.

`paylab worker --once` processes at most one queued job and is useful for scripts and smoke tests.

### Community provider SDK

Third-party payment providers can plug into PayLab as separate Python packages through the `paylab.providers` entry-point group. Contributors no longer need to edit the PayLab core registry to add an adapter.

```toml
[project.entry-points."paylab.providers"]
acmepay = "paylab_acmepay:AcmePayAdapter"
```

After installing the plugin in the same environment and restarting PayLab, it appears in `GET /v1/providers` and works through normal triggers, chaos tests, history, live streaming, and Redis workers.

See [docs/provider-sdk.md](docs/provider-sdk.md) for the adapter contract, packaging example, worker secret naming, and testing checklist.

`@main` is the v0.5 preview channel. A stable `v0.5.0` tag will be published only after the complete milestone passes its release checks.

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
paylab lifecycle paystack http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --out-of-order
```

## Checkout chaos suite

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --html paylab-report.html
```

## Retry storms

```powershell
paylab storm paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --attempts 10 --interval 0.05
```

## Persistent history

SQLite defaults to `~/.paylab/paylab.db`. Use `PAYLAB_DB_PATH` to change it, or configure PostgreSQL with `PAYLAB_DATABASE_URL`.

```powershell
paylab history --provider paystack --limit 10
```

PayLab deliberately does **not** persist or stream webhook signing secrets or raw signed webhook bodies.

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

## Roadmap

### v0.5

- [x] GitHub Action and CI reliability gates
- [x] PostgreSQL history backend with integration tests
- [x] Redis-backed multi-process live streaming
- [x] Redis delivery job queue + worker CLI
- [x] Community provider SDK
- [ ] Additional provider adapters
- [ ] Stable `v0.5.0` release tag and launch assets

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
