from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from paylab.gate import run_reliability_gate, write_gate_reports, write_github_outputs
from paylab.models import ChaosRequest


@dataclass(frozen=True)
class ActionConfig:
    request: ChaosRequest
    min_score: int
    json_report: Path
    html_report: Path


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"missing required environment variable: {name}")
    return value


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError("boolean input must be true or false")


def _safe_path(value: str) -> Path:
    if "\n" in value or "\r" in value:
        raise ValueError("report paths cannot contain newlines")
    return Path(value)


def load_action_config() -> ActionConfig:
    probe_url = os.getenv("PAYLAB_PROBE_URL", "").strip() or None
    request = ChaosRequest(
        provider=_required("PAYLAB_PROVIDER"),
        event=_required("PAYLAB_EVENT"),
        target_url=_required("PAYLAB_TARGET_URL"),
        secret=_required("PAYLAB_SECRET"),
        duplicate_count=int(os.getenv("PAYLAB_DUPLICATE", "3")),
        delay_seconds=float(os.getenv("PAYLAB_DELAY", "1")),
        enable_fault_injection=_as_bool(os.getenv("PAYLAB_DEEP", "false")),
        probe_url=probe_url,
        retry_count=int(os.getenv("PAYLAB_RETRY", "2")),
        timeout_seconds=float(os.getenv("PAYLAB_TIMEOUT", "0.15")),
        metadata={"paylab_ci": True},
    )
    min_score = int(os.getenv("PAYLAB_MIN_SCORE", "100"))
    if not 0 <= min_score <= 100:
        raise ValueError("PAYLAB_MIN_SCORE must be between 0 and 100")
    return ActionConfig(
        request=request,
        min_score=min_score,
        json_report=_safe_path(os.getenv("PAYLAB_JSON_REPORT", "paylab-report.json")),
        html_report=_safe_path(os.getenv("PAYLAB_HTML_REPORT", "paylab-report.html")),
    )


def _print_summary(config: ActionConfig, *, percentage: int, grade: str, passed: bool) -> None:
    marker = "PASS" if passed else "FAIL"
    print(
        f"PayLab CI gate: {marker} | {percentage}% | Grade {grade} | "
        f"threshold {config.min_score}%"
    )
    print(f"Provider: {config.request.provider} | Event: {config.request.event}")
    print(f"Target: {config.request.target_url}")


def main() -> int:
    try:
        config = load_action_config()
    except (ValueError, ValidationError):
        print(
            "PayLab Action configuration is invalid. Check provider, URLs, and numeric inputs.",
            file=sys.stderr,
        )
        return 1

    try:
        result = asyncio.run(
            run_reliability_gate(config.request, min_score=config.min_score)
        )
        json_path, html_path = write_gate_reports(
            result,
            json_path=config.json_report,
            html_path=config.html_report,
        )
        output_file = os.getenv("GITHUB_OUTPUT", "").strip()
        if output_file:
            write_github_outputs(
                result,
                output_file=output_file,
                json_report=json_path,
                html_report=html_path,
            )
    except (OSError, ValueError) as exc:
        print(f"PayLab Action failed to write its reports or outputs: {exc}", file=sys.stderr)
        return 1

    _print_summary(
        config,
        percentage=result.percentage,
        grade=result.report.grade,
        passed=result.passed,
    )
    print(f"JSON report: {config.json_report.resolve()}")
    print(f"HTML report: {config.html_report.resolve()}")

    if result.passed:
        if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
            print(
                "::notice title=PayLab reliability gate passed::"
                f"Score {result.percentage}% (threshold {result.threshold}%)"
            )
        return 0

    if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
        print(
            "::error title=PayLab reliability gate failed::"
            f"Score {result.percentage}% is below threshold {result.threshold}%"
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
