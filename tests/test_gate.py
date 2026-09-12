from pathlib import Path

import pytest

from paylab.gate import (
    evaluate_reliability_gate,
    gate_payload,
    reliability_percentage,
    write_gate_reports,
    write_github_outputs,
)
from paylab.models import ChaosResponse, ChaosScenarioResult


def _report(score: int, max_score: int = 100) -> ChaosResponse:
    return ChaosResponse(
        provider="paystack",
        event="charge.success",
        target_url="http://merchant.test/webhook",
        score=score,
        max_score=max_score,
        grade="A" if score == max_score else "B",
        scenarios=[
            ChaosScenarioResult(
                name="baseline",
                description="baseline",
                passed=score == max_score,
                points=score,
                max_points=max_score,
                evidence="HTTP 200",
            )
        ],
    )


def test_gate_passes_at_threshold() -> None:
    result = evaluate_reliability_gate(_report(80), min_score=80)
    assert result.passed is True
    assert result.percentage == 80


def test_gate_fails_below_threshold() -> None:
    result = evaluate_reliability_gate(_report(79), min_score=80)
    assert result.passed is False


def test_gate_uses_percentage_for_non_100_maximum() -> None:
    report = _report(150, 175)
    assert reliability_percentage(report) == 86
    assert evaluate_reliability_gate(report, min_score=85).passed is True


def test_gate_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        evaluate_reliability_gate(_report(100), min_score=101)


def test_gate_reports_and_github_outputs_are_secret_free(tmp_path: Path) -> None:
    result = evaluate_reliability_gate(_report(100), min_score=100)
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    output_path = tmp_path / "github-output.txt"

    write_gate_reports(result, json_path=json_path, html_path=html_path)
    write_github_outputs(
        result,
        output_file=output_path,
        json_report=json_path,
        html_report=html_path,
    )

    combined = json_path.read_text() + html_path.read_text() + output_path.read_text()
    assert "super-secret-value" not in combined
    assert gate_payload(result)["passed"] is True
    assert "passed=true" in output_path.read_text()
    assert "percentage=100" in output_path.read_text()
