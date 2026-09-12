from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from paylab.chaos import run_checkout_chaos
from paylab.models import ChaosRequest, ChaosResponse
from paylab.reporting import render_chaos_report


@dataclass(frozen=True)
class ReliabilityGateResult:
    report: ChaosResponse
    threshold: int
    percentage: int
    passed: bool


def reliability_percentage(report: ChaosResponse) -> int:
    if report.max_score <= 0:
        return 0
    return round((report.score / report.max_score) * 100)


def evaluate_reliability_gate(
    report: ChaosResponse,
    *,
    min_score: int = 100,
) -> ReliabilityGateResult:
    if not 0 <= min_score <= 100:
        raise ValueError("min_score must be between 0 and 100")
    percentage = reliability_percentage(report)
    return ReliabilityGateResult(
        report=report,
        threshold=min_score,
        percentage=percentage,
        passed=percentage >= min_score,
    )


async def run_reliability_gate(
    request: ChaosRequest,
    *,
    min_score: int = 100,
) -> ReliabilityGateResult:
    report = await run_checkout_chaos(request)
    return evaluate_reliability_gate(report, min_score=min_score)


def gate_payload(result: ReliabilityGateResult) -> dict[str, object]:
    return {
        "passed": result.passed,
        "threshold": result.threshold,
        "percentage": result.percentage,
        "score": result.report.score,
        "max_score": result.report.max_score,
        "grade": result.report.grade,
        "report": result.report.model_dump(mode="json"),
    }


def write_gate_reports(
    result: ReliabilityGateResult,
    *,
    json_path: str | Path | None = None,
    html_path: str | Path | None = None,
) -> tuple[Path | None, Path | None]:
    written_json: Path | None = None
    written_html: Path | None = None

    if json_path is not None:
        written_json = Path(json_path)
        written_json.parent.mkdir(parents=True, exist_ok=True)
        written_json.write_text(
            json.dumps(gate_payload(result), indent=2),
            encoding="utf-8",
        )

    if html_path is not None:
        written_html = Path(html_path)
        written_html.parent.mkdir(parents=True, exist_ok=True)
        written_html.write_text(render_chaos_report(result.report), encoding="utf-8")

    return written_json, written_html


def _safe_output_value(value: object) -> str:
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ValueError("GitHub Action output values cannot contain newlines")
    return text


def write_github_outputs(
    result: ReliabilityGateResult,
    *,
    output_file: str | Path,
    json_report: str | Path | None = None,
    html_report: str | Path | None = None,
) -> None:
    values = {
        "score": result.report.score,
        "max_score": result.report.max_score,
        "percentage": result.percentage,
        "grade": result.report.grade,
        "passed": str(result.passed).lower(),
        "json_report": Path(json_report).resolve() if json_report is not None else "",
        "html_report": Path(html_report).resolve() if html_report is not None else "",
    }
    destination = Path(output_file)
    with destination.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={_safe_output_value(value)}\n")
