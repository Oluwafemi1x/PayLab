from paylab.models import ChaosResponse, ChaosScenarioResult
from paylab.reporting import render_chaos_report


def test_report_escapes_evidence() -> None:
    report = ChaosResponse(provider="paystack", event="charge.success", target_url="http://merchant.test/webhook", score=25, max_score=25, grade="A", scenarios=[ChaosScenarioResult(name="baseline", description="ok", passed=True, points=25, max_points=25, evidence="<script>alert(1)</script>")])
    html = render_chaos_report(report)
    assert "PayLab Reliability Report" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
