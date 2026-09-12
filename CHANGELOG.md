# Changelog

## 0.5.0 — 2026-09-12

- Added a reusable GitHub Action with configurable CI reliability thresholds and secret-safe JSON/HTML reports.
- Added an optional PostgreSQL history backend with native `JSONB`, safe upserts, Docker support, and real Postgres integration tests.
- Added optional Redis Pub/Sub live streaming selected with `PAYLAB_REDIS_URL`.
- Added cross-process live event fan-out so separate PayLab API processes can feed the same WebSocket/dashboard stream.
- Added a secret-safe Redis background delivery queue and worker with asynchronous job status APIs.
- Added the Community Provider SDK with `paylab.providers` entry-point discovery and built-in collision protection.
- Added Monnify as a built-in provider with production-style `monnify-signature` HMAC-SHA512 signing, collection/refund fixtures, lifecycle defaults, and worker secret support.
- Added Razorpay as a built-in provider with raw-body HMAC-SHA256 `X-Razorpay-Signature`, `x-razorpay-event-id`, payment/refund fixtures, lifecycle defaults, and worker secret support.
- Hardened programmatic provider registration so invalid adapters and name mismatches fail explicitly.
- Added package/runtime version-consistency regression coverage.
- Kept in-memory streaming as the zero-config default and kept signing secrets/raw webhook bodies out of live stream and job payloads.

## 0.4.0

- Added a live browser dashboard at `/dashboard` with recent event metrics and webhook activity.
- Added the `/v1/stream` WebSocket endpoint for real-time delivery events.
- Added lifecycle simulation with provider defaults, custom sequences, and reversed out-of-order delivery.
- Added `paylab lifecycle` for running lifecycle sequences from the CLI.
- Added standalone HTML chaos reports through `paylab chaos checkout --html report.html`.
- Added `POST /v1/chaos/checkout/report` for server-rendered HTML reliability reports.
- Live stream payloads intentionally exclude webhook secrets and raw signed bodies.
- Expanded automated coverage for streaming, lifecycle ordering, dashboard delivery, WebSocket handshake, and report escaping.

## 0.3.0

- Added persistent SQLite event history without storing webhook secrets or raw signed payloads.
- Added `GET /v1/history/events` and `GET /v1/history/events/{event_id}`.
- Added `paylab history` for inspecting recent webhook simulations.
- Added retry-on-timeout/HTTP-5xx behavior with configurable retry count, delay, and timeout.
- Added `paylab storm` for rapid repeated delivery of one event ID.
- Added opt-in `--deep` checkout chaos checks for fail-once and timeout-once recovery.
- Added optional business-level idempotency probing through `--probe-url`.
- Expanded the demo merchant with fault injection and a test-only idempotency probe.
- Expanded automated tests from 12 to 19.

## 0.2.0

- Added `paylab chaos checkout`.
- Added `/v1/chaos/checkout` API endpoint.
- Added four automated reliability scenarios: baseline delivery, duplicate delivery, invalid signature, and delayed delivery.
- Added 0-100 reliability scoring and A-D grading.
- Added `--json` output for automation and future CI integration.
- Expanded automated tests from 6 to 12.

## 0.1.0

- Initial Paystack, Stripe, and Flutterwave webhook simulation.
- Added duplicate, delay, and invalid-signature controls.
- Added CLI, FastAPI API, Docker files, demo merchant, and tests.
