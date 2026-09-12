# PayLab Community Provider SDK

PayLab providers can live in separate Python packages. A provider plugin only needs to implement `ProviderAdapter` and publish a Python entry point in the `paylab.providers` group.

This lets contributors add payment providers without editing or forking PayLab core.

## 1. Create an adapter

```python
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any

from paylab.providers import ProviderAdapter
from paylab.providers.base import BuiltEvent


class AcmePayAdapter(ProviderAdapter):
    name = "acmepay"

    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        event_id = f"acme_{secrets.token_hex(8)}"
        payload = {
            "event": event_type,
            "data": {
                "id": event_id,
                "metadata": {"paylab_event_id": event_id, **metadata},
            },
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        signing_secret = "invalid-secret" if invalid_signature else secret
        signature = hmac.new(signing_secret.encode(), body, hashlib.sha256).hexdigest()
        return BuiltEvent(
            event_id=event_id,
            body=body,
            headers={
                "content-type": "application/json",
                "x-acmepay-signature": signature,
                "x-paylab-event-id": event_id,
            },
        )
```

The adapter must return a `BuiltEvent` containing:

- a stable test event ID;
- the exact raw webhook body as bytes;
- provider-compatible HTTP headers, including the signature header.

`invalid_signature=True` must deliberately produce a signature the merchant should reject.

## 2. Register the package entry point

In the plugin package's `pyproject.toml`:

```toml
[project]
name = "paylab-acmepay"
version = "0.1.0"
dependencies = ["paylab-dev>=0.5.0.dev0,<0.6"]

[project.entry-points."paylab.providers"]
acmepay = "paylab_acmepay:AcmePayAdapter"
```

The entry-point name and `adapter.name` must match. Provider names are lowercase and may contain letters, digits, `.`, `_`, and `-`.

Plugins cannot silently replace built-in providers such as `paystack`, `stripe`, `flutterwave`, `monnify`, or `razorpay`.

## 3. Install and use it

Install PayLab and the provider package in the same Python environment, then restart PayLab:

```bash
pip install paylab-acmepay
paylab start
```

The plugin is automatically discovered. It appears in `GET /v1/providers` and works through the normal trigger, chaos, history, live-stream, and queued-worker paths.

```bash
paylab trigger acmepay payment.succeeded http://127.0.0.1:9000/webhooks/acmepay --secret test_secret
```

## Background workers

Queued jobs never store provider signing secrets. For a plugin named `acme-pay`, the worker resolves the secret from:

```text
PAYLAB_ACME_PAY_SECRET=...
```

Provider punctuation is converted to `_` for environment-variable names.

## Lifecycle testing

Built-in providers have default lifecycle sequences. Community providers should pass an explicit sequence until the plugin lifecycle contract is expanded:

```bash
paylab lifecycle acmepay http://127.0.0.1:9000/webhooks/acmepay \
  --secret test_secret \
  --events payment.pending,payment.succeeded,refund.completed
```

## Testing a provider plugin

At minimum, test:

1. normal signatures are accepted by a representative receiver;
2. `invalid_signature=True` is rejected;
3. metadata includes a PayLab event/correlation ID where the provider format allows it;
4. duplicate delivery reuses the same built event;
5. retries and timeouts do not change the provider event identity;
6. no signing secret appears in payloads, history, streams, reports, or Redis jobs.

A plugin can also be registered programmatically for tests:

```python
from paylab.providers import register_provider

register_provider(AcmePayAdapter())
```

Use a separate process for production/plugin discovery through entry points; `register_provider()` is primarily intended for tests and embedded integrations.

## Compatibility contract

For the v0.5 SDK, third-party providers should depend on the public interfaces below:

- `paylab.providers.ProviderAdapter`
- `paylab.providers.base.BuiltEvent`
- the `paylab.providers` entry-point group

Everything else should be treated as internal unless documented as public in a future release.
