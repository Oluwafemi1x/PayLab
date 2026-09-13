# PayLab launch demo

This guide turns PayLab into a short, repeatable product demo for GitHub, GitHub Marketplace, LinkedIn, X, Reddit, DEV, and technical interviews.

> **Core message:** Break your payment integration before your customers do.

## What the demo proves

In one run, the launch demo shows that PayLab can:

1. deliver a correctly signed payment webhook;
2. send duplicate webhook deliveries;
3. send an invalid signature and verify that the merchant rejects it;
4. send lifecycle events out of order;
5. run the checkout chaos suite with retry/fault recovery;
6. probe business-level idempotency;
7. show activity on the live dashboard;
8. generate an HTML reliability report.

## Windows quick start

From the PayLab repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\examples\launch_demo.ps1
```

The script checks whether PayLab and the bundled demo merchant are already running. If they are not, it starts them automatically.

It then opens:

- PayLab dashboard: `http://127.0.0.1:8787/dashboard`
- the generated HTML reliability report at the end of the run

By default the script pauses between scenes so you can record each moment cleanly.

To run the whole sequence without pauses:

```powershell
.\examples\launch_demo.ps1 -Auto
```

To avoid automatically opening the browser/report:

```powershell
.\examples\launch_demo.ps1 -SkipOpen
```

## Recommended recording layout

Use a 16:9 desktop recording.

Place the PayLab dashboard on the left half of the screen and PowerShell on the right half. Keep the text large enough to read on a phone after the video is compressed by social platforms.

Do not show real payment-provider secrets, customer data, browser bookmarks, email notifications, API keys, or unrelated windows.

The bundled demo uses only local test secrets and a local demo merchant.

## 30-second launch cut

### Scene 1 — Hook (0–4s)

Show the dashboard and terminal.

On-screen text:

> Payment bugs should not first appear when real money moves.

Narration:

> "I built PayLab to break payment webhooks safely before customers find the bugs in production."

### Scene 2 — Duplicate webhooks (4–10s)

Run or show the duplicate-delivery stage.

Focus on:

```text
attempt 1 (delivery 1, retry 0)
attempt 2 (delivery 2, retry 0)
attempt 3 (delivery 3, retry 0)
```

Narration:

> "Here PayLab sends the same payment webhook three times to test idempotency."

### Scene 3 — Bad signature (10–15s)

Show the invalid-signature stage.

Narration:

> "Then it deliberately signs a webhook incorrectly to verify that the integration rejects it."

### Scene 4 — Chaos suite (15–24s)

Show the checkout chaos report and reliability score.

Narration:

> "The chaos suite tests retries, failures, timeouts, ordering and duplicate business effects, then gives the integration a reliability score."

### Scene 5 — CI message (24–30s)

Show the GitHub Action snippet or the HTML report.

On-screen text:

> Fail CI before payment failures reach production.

Narration:

> "And the same reliability gate can run directly inside GitHub Actions. PayLab is open source."

End card:

> PayLab — Break your payment integration before your customers do.

## 2-minute technical demo

For a longer technical demo, use the guided script without `-Auto` and explain each stage.

Suggested structure:

- **0:00–0:15** — problem and PayLab dashboard
- **0:15–0:30** — healthy signed webhook
- **0:30–0:50** — duplicate delivery and idempotency
- **0:50–1:05** — invalid signature
- **1:05–1:20** — out-of-order lifecycle
- **1:20–1:45** — deep checkout chaos suite
- **1:45–2:00** — HTML report + GitHub Actions reliability gate

## Manual commands

If you prefer to run each step yourself, use three terminals.

### Terminal 1 — PayLab API

```powershell
.\.venv\Scripts\Activate.ps1
paylab start
```

### Terminal 2 — demo merchant

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn examples.demo_receiver:app --port 9000
```

### Terminal 3 — scenarios

Healthy webhook:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab
```

Duplicate delivery:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --duplicate 3
```

Invalid signature:

```powershell
paylab trigger paystack charge.success http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --invalid-signature
```

Out-of-order lifecycle:

```powershell
paylab lifecycle paystack http://127.0.0.1:9000/webhooks/paystack --secret sk_test_paylab --out-of-order
```

Deep checkout chaos suite with idempotency probe and HTML report:

```powershell
paylab chaos checkout paystack charge.success http://127.0.0.1:9000/webhooks/paystack `
  --secret sk_test_paylab `
  --deep `
  --probe-url http://127.0.0.1:9000/paylab/probe `
  --html paylab-demo-report.html
```

## What to capture for launch assets

Keep these screenshots/clips after recording:

- dashboard with multiple webhook deliveries;
- terminal showing the three duplicate deliveries;
- invalid-signature rejection;
- final chaos reliability score and grade;
- HTML reliability report;
- GitHub Actions workflow using `Oluwafemi1x/PayLab@v0.5.0`.

Those six assets can be reused across the README, Marketplace listing, X, LinkedIn, Reddit, DEV/Hashnode, and Show HN.
