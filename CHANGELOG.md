# Changelog

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
