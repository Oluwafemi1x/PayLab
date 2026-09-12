import json
from pathlib import Path
from typing import Annotated

import httpx
import typer
import uvicorn

from paylab.models import ChaosResponse
from paylab.reporting import render_chaos_report

app = typer.Typer(
    help="PayLab — break your payment integration before your customers do.",
    no_args_is_help=True,
)
chaos_app = typer.Typer(help="Run payment reliability chaos scenarios.", no_args_is_help=True)
app.add_typer(chaos_app, name="chaos")


@app.command()
def start(
    host: Annotated[str, typer.Option(help="Host to bind to.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to bind to.")] = 8787,
    reload: Annotated[bool, typer.Option(help="Enable development reload.")] = False,
) -> None:
    """Start the PayLab API server."""
    uvicorn.run("paylab.api:app", host=host, port=port, reload=reload)


@app.command()
def trigger(
    provider: Annotated[str, typer.Argument(help="paystack, stripe, or flutterwave")],
    event: Annotated[str, typer.Argument(help="Provider event type")],
    target_url: Annotated[str, typer.Argument(help="Your webhook endpoint")],
    secret: Annotated[str, typer.Option("--secret", "-s", help="Webhook signing secret")],
    duplicate: Annotated[int, typer.Option("--duplicate", "-d", help="Delivery count")] = 1,
    delay: Annotated[float, typer.Option("--delay", help="Delay before delivery, seconds")] = 0,
    retry: Annotated[int, typer.Option("--retry", help="Retries after timeout/HTTP 5xx")] = 0,
    retry_delay: Annotated[
        float, typer.Option("--retry-delay", help="Seconds between retries")
    ] = 0.1,
    timeout: Annotated[
        float, typer.Option("--timeout", help="Per-delivery HTTP timeout in seconds")
    ] = 10.0,
    invalid_signature: Annotated[
        bool, typer.Option("--invalid-signature", help="Sign with the wrong secret")
    ] = False,
    server: Annotated[
        str, typer.Option("--server", help="Running PayLab server")
    ] = "http://127.0.0.1:8787",
) -> None:
    """Trigger a simulated payment webhook."""
    payload = {
        "provider": provider,
        "event": event,
        "target_url": target_url,
        "secret": secret,
        "duplicate": duplicate,
        "delay_seconds": delay,
        "retry_count": retry,
        "retry_delay_seconds": retry_delay,
        "timeout_seconds": timeout,
        "invalid_signature": invalid_signature,
    }
    try:
        response = httpx.post(f"{server.rstrip('/')}/v1/events/trigger", json=payload, timeout=75)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"PayLab request failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    data = response.json()
    typer.echo(f"Event: {data['event_id']} ({data['provider']} / {data['event']})")
    for delivery in data["deliveries"]:
        detail = f"delivery {delivery['delivery_index']}, retry {delivery['retry_index']}"
        if delivery.get("error"):
            typer.echo(f"  attempt {delivery['attempt']} ({detail}): ERROR {delivery['error']}")
        else:
            typer.echo(
                f"  attempt {delivery['attempt']} ({detail}): HTTP {delivery['status_code']} "
                f"({delivery['latency_ms']} ms)"
            )


@app.command()
def lifecycle(
    provider: Annotated[str, typer.Argument(help="paystack, stripe, or flutterwave")],
    target_url: Annotated[str, typer.Argument(help="Your webhook endpoint")],
    secret: Annotated[str, typer.Option("--secret", "-s", help="Webhook signing secret")],
    events: Annotated[
        str | None,
        typer.Option("--events", help="Comma-separated event sequence; defaults by provider"),
    ] = None,
    out_of_order: Annotated[
        bool, typer.Option("--out-of-order", help="Reverse the lifecycle event order")
    ] = False,
    interval: Annotated[
        float, typer.Option("--interval", help="Seconds between lifecycle events")
    ] = 0.1,
    server: Annotated[
        str, typer.Option("--server", help="Running PayLab server")
    ] = "http://127.0.0.1:8787",
) -> None:
    """Run a payment lifecycle sequence, optionally out of order."""
    event_list = [item.strip() for item in events.split(",") if item.strip()] if events else None
    payload = {
        "provider": provider,
        "target_url": target_url,
        "secret": secret,
        "events": event_list,
        "out_of_order": out_of_order,
        "interval_seconds": interval,
    }
    try:
        response = httpx.post(f"{server.rstrip('/')}/v1/lifecycle", json=payload, timeout=90)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"PayLab lifecycle request failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    data = response.json()
    typer.echo(f"Lifecycle: {data['lifecycle_id']} ({data['provider']})")
    for step in data["steps"]:
        marker = "ACK" if step["acknowledged"] else "FAIL"
        typer.echo(
            f"  {step['step']}. [{marker}] {step['event']} "
            f"event_id={step['event_id']} statuses={step['status_codes']}"
        )


@app.command()
def storm(
    provider: Annotated[str, typer.Argument(help="paystack, stripe, or flutterwave")],
    event: Annotated[str, typer.Argument(help="Provider event type")],
    target_url: Annotated[str, typer.Argument(help="Your webhook endpoint")],
    secret: Annotated[str, typer.Option("--secret", "-s", help="Webhook signing secret")],
    attempts: Annotated[
        int, typer.Option("--attempts", "-n", help="Number of repeated deliveries")
    ] = 10,
    interval: Annotated[
        float, typer.Option("--interval", help="Seconds between repeated deliveries")
    ] = 0.05,
    server: Annotated[
        str, typer.Option("--server", help="Running PayLab server")
    ] = "http://127.0.0.1:8787",
) -> None:
    """Send a rapid repeated-delivery storm using one event ID."""
    payload = {
        "provider": provider,
        "event": event,
        "target_url": target_url,
        "secret": secret,
        "duplicate": attempts,
        "delivery_interval_seconds": interval,
    }
    try:
        response = httpx.post(
            f"{server.rstrip('/')}/v1/events/trigger",
            json=payload,
            timeout=max(75.0, attempts * interval + 30.0),
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"PayLab storm request failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    data = response.json()
    successful = sum(
        1
        for item in data["deliveries"]
        if item.get("status_code") is not None and 200 <= item["status_code"] < 300
    )
    typer.echo(
        f"Storm event {data['event_id']}: {successful}/{len(data['deliveries'])} "
        "deliveries acknowledged"
    )


@app.command("history")
def history_command(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum events to show")] = 20,
    provider: Annotated[
        str | None, typer.Option("--provider", help="Filter by payment provider")
    ] = None,
    server: Annotated[
        str, typer.Option("--server", help="Running PayLab server")
    ] = "http://127.0.0.1:8787",
) -> None:
    """Show persisted PayLab event history."""
    params: dict[str, object] = {"limit": limit}
    if provider:
        params["provider"] = provider
    try:
        response = httpx.get(
            f"{server.rstrip('/')}/v1/history/events", params=params, timeout=15
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"PayLab history request failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    events_data = response.json()
    if not events_data:
        typer.echo("No PayLab events recorded yet.")
        return
    for item in events_data:
        typer.echo(
            f"{item['created_at']}  {item['event_id']}  "
            f"{item['provider']} / {item['event']}  attempts={len(item['deliveries'])}"
        )


@chaos_app.command("checkout")
def chaos_checkout(
    provider: Annotated[str, typer.Argument(help="paystack, stripe, or flutterwave")],
    event: Annotated[str, typer.Argument(help="Provider success event type")],
    target_url: Annotated[str, typer.Argument(help="Your webhook endpoint")],
    secret: Annotated[str, typer.Option("--secret", "-s", help="Webhook signing secret")],
    duplicate: Annotated[
        int, typer.Option("--duplicate", "-d", help="Duplicate delivery count")
    ] = 3,
    delay: Annotated[
        float, typer.Option("--delay", help="Delayed-delivery scenario in seconds")
    ] = 1.0,
    deep: Annotated[
        bool,
        typer.Option(
            "--deep",
            help="Enable opt-in fail-once and timeout-once fault-injection checks",
        ),
    ] = False,
    probe_url: Annotated[
        str | None,
        typer.Option(
            "--probe-url",
            help="Optional test-only endpoint returning deliveries_received and side_effect_count",
        ),
    ] = None,
    retry: Annotated[int, typer.Option("--retry", help="Retries for deep fault checks")] = 2,
    timeout: Annotated[
        float, typer.Option("--timeout", help="Timeout used by deep timeout-recovery check")
    ] = 0.15,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON")
    ] = False,
    html_report: Annotated[
        str | None, typer.Option("--html", help="Write a standalone HTML reliability report")
    ] = None,
    server: Annotated[
        str, typer.Option("--server", help="Running PayLab server")
    ] = "http://127.0.0.1:8787",
) -> None:
    """Run the checkout reliability suite."""
    payload = {
        "provider": provider,
        "event": event,
        "target_url": target_url,
        "secret": secret,
        "duplicate_count": duplicate,
        "delay_seconds": delay,
        "enable_fault_injection": deep,
        "retry_count": retry,
        "timeout_seconds": timeout,
        "probe_url": probe_url,
    }
    try:
        response = httpx.post(
            f"{server.rstrip('/')}/v1/chaos/checkout",
            json=payload,
            timeout=max(90.0, delay + 45.0),
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"PayLab chaos request failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    data = response.json()
    if html_report:
        report_path = Path(html_report)
        report_path.write_text(
            render_chaos_report(ChaosResponse.model_validate(data)),
            encoding="utf-8",
        )
        typer.echo(f"HTML report: {report_path.resolve()}")

    if json_output:
        typer.echo(json.dumps(data, indent=2))
        return

    typer.echo("\nPAYLAB CHECKOUT CHAOS REPORT")
    typer.echo("=" * 30)
    typer.echo(f"Provider: {data['provider']}")
    typer.echo(f"Event:    {data['event']}")
    typer.echo(f"Target:   {data['target_url']}")
    typer.echo("")
    for scenario in data["scenarios"]:
        marker = "PASS" if scenario["passed"] else "FAIL"
        typer.echo(
            f"[{marker}] {scenario['name']} "
            f"({scenario['points']}/{scenario['max_points']})"
        )
        typer.echo(f"       {scenario['evidence']}")
    typer.echo("")
    typer.echo(f"Reliability score: {data['score']}/{data['max_score']}  Grade: {data['grade']}")

    if data["score"] < data["max_score"]:
        raise typer.Exit(code=2)
