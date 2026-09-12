# PayLab v0.5.0 Release Checklist

This checklist is the final quality gate for the first coordinated public PayLab launch.

## Code quality

- [x] Ruff passes on Python 3.11, 3.12, and 3.13.
- [x] Full pytest suite passes on Python 3.11, 3.12, and 3.13.
- [x] PayLab Action smoke test passes.
- [x] PostgreSQL integration test passes against a real PostgreSQL service.
- [x] Redis stream/worker integration test passes against a real Redis service.
- [x] Runtime and package versions are covered by a regression test.

## v0.5 capabilities

- [x] GitHub Action reliability gate.
- [x] PostgreSQL history backend.
- [x] Redis multi-process live streaming.
- [x] Redis background webhook delivery queue and worker.
- [x] Community provider SDK and Python entry-point discovery.
- [x] Paystack, Stripe, Flutterwave, Monnify, and Razorpay built-in providers.
- [x] Payment lifecycle and out-of-order testing.
- [x] Duplicate, delayed, invalid-signature, retry, timeout, and failure scenarios.
- [x] Secret-safe reports, history, streams, and queued jobs.

## Release requirements

- [ ] Package/runtime version changed from `0.5.0.dev0` to `0.5.0`.
- [ ] README no longer labels v0.5 as preview.
- [ ] CHANGELOG contains a final `0.5.0` section.
- [ ] Release branch passes the full GitHub gate set.
- [ ] Release commit is merged into `main`.
- [ ] The merged `main` commit passes the full gate set again.
- [ ] Git tag `v0.5.0` created from the verified release commit.
- [ ] GitHub Release published with launch-ready notes.

Do not tag or publish the release while any required check is failing or still pending.
