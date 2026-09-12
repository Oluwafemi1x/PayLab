import json
from typing import Annotated

import httpx
import typer
import uvicorn

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
        if delivery.get("error"):
            typer.echo(f"  attempt {delivery['attempt']}: ERROR {delivery['error']}")
        else:
            typer.echo(
                f"  attempt {delivery['attempt']}: HTTP {delivery['status_code']} "
                f"({delivery['latency_ms']} ms)"
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
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON")
    ] = False,
    server: Annotated[
        str, typer.Option("--server", help="Running PayLab server")
    ] = "http://127.0.0.1:8787",
) -> None:
    """Run the v0.2 checkout reliability suite."""
    payload = {
        "provider": provider,
        "event": event,
        "target_url": target_url,
        "secret": secret,
        "duplicate_count": duplicate,
        "delay_seconds": delay,
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
    typer.echo(
        "Note: duplicate acknowledgement does not by itself prove that your database/order logic is idempotent."
    )

    if data["score"] < data["max_score"]:
        raise typer.Exit(code=2)
