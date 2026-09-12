# Changelog

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
