# Security Policy

PayLab is a testing tool. Never commit real payment credentials, production webhook secrets,
or customer data to fixtures or issue reports.

The `x-paylab-fault` protocol used by the v0.3 deep chaos suite is **test-only**. Do not add
fault-injection behavior to a production webhook endpoint unless it is strongly isolated and
cannot be triggered by untrusted traffic. The bundled demo receiver is intended for local
development only.

PayLab event history deliberately does not persist webhook secrets or raw signed webhook bodies.

If you discover a security issue, do not open a public issue containing exploit details.
Contact the maintainer privately first.
