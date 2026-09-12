from __future__ import annotations

from html import escape

from paylab.models import ChaosResponse


def render_chaos_report(report: ChaosResponse) -> str:
    rows = []
    for scenario in report.scenarios:
        status = "PASS" if scenario.passed else "FAIL"
        rows.append(
            "<tr>"
            f"<td>{escape(status)}</td>"
            f"<td>{escape(scenario.name)}</td>"
            f"<td>{scenario.points}/{scenario.max_points}</td>"
            f"<td>{escape(scenario.evidence)}</td>"
            "</tr>"
        )
    rows_html = "".join(rows)
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PayLab Reliability Report</title>
<style>body{{font-family:Inter,system-ui,sans-serif;margin:0;background:#0b1020;color:#eaf0ff}}main{{max-width:960px;margin:48px auto;padding:0 20px}}.card{{background:#131a2d;border:1px solid #26304c;border-radius:16px;padding:24px;margin-bottom:20px}}h1{{margin-top:0}}.score{{font-size:44px;font-weight:800}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #26304c;vertical-align:top}}small{{color:#9daccc}}</style>
</head><body><main><div class="card"><small>PAYLAB RELIABILITY REPORT</small><h1>{escape(report.provider)} / {escape(report.event)}</h1><div class="score">{report.score}/{report.max_score} · Grade {escape(report.grade)}</div><p>{escape(report.target_url)}</p></div><div class="card"><table><thead><tr><th>Status</th><th>Scenario</th><th>Score</th><th>Evidence</th></tr></thead><tbody>{rows_html}</tbody></table></div></main></body></html>"""
