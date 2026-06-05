from __future__ import annotations

import json

from scripts import run_narrative_source_coverage_gap_report
from src.scanners.narrative_source_coverage_gap import (
    build_narrative_source_coverage_gap_report,
    render_narrative_source_coverage_gap_html,
)


def test_source_coverage_gap_report_classifies_gateway_backlog():
    report = build_narrative_source_coverage_gap_report(
        gateway_probe=_gateway_probe_payload(),
        generated_at="2026-06-05T10:00:00+00:00",
    )

    assert report["version"] == "narrative-source-coverage-gap-report-v1"
    assert report["status"] == "degraded"
    assert report["summary"] == {
        "expected_source_kind_count": 7,
        "working_count": 2,
        "missing_count": 3,
        "degraded_count": 2,
        "unsupported_count": 1,
        "auto_created_issue_count": 0,
    }
    by_kind = {gap["source_kind"]: gap for gap in report["gaps"]}
    assert by_kind["official_filings"]["coverage_status"] == "working"
    assert by_kind["official_sources"]["coverage_status"] == "missing"
    assert by_kind["open_news_index"]["coverage_status"] == "degraded"
    assert by_kind["social_heat"]["owner"] == "Gateway"
    assert by_kind["paid_provider_later"]["coverage_status"] == "unsupported"
    assert by_kind["paid_provider_later"]["owner"] == "Later"
    assert all(gap["auto_create_issue"] is False for gap in report["gaps"])


def test_source_coverage_gap_html_is_chinese_and_owner_oriented():
    html = render_narrative_source_coverage_gap_html(
        build_narrative_source_coverage_gap_report(
            gateway_probe=_gateway_probe_payload(),
            generated_at="2026-06-05T10:00:00+00:00",
        )
    )

    assert "<h1>Gateway 来源覆盖缺口报告</h1>" in html
    assert "不会自动创建 Linear issue" in html
    assert "官方披露文件" in html
    assert "付费来源暂缓" in html
    assert "REQUEST_TIMEOUT" in html


def test_source_coverage_gap_cli_writes_json_html(tmp_path):
    input_path = tmp_path / "gateway_probe.json"
    input_path.write_text(
        json.dumps(_gateway_probe_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_narrative_source_coverage_gap_report.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "coverage_gap"),
        ]
    )

    payload = json.loads(
        (tmp_path / "coverage_gap" / "narrative_source_coverage_gap.json").read_text()
    )
    html = (
        tmp_path / "coverage_gap" / "narrative_source_coverage_gap.html"
    ).read_text()

    assert exit_code == 0
    assert payload["summary"]["auto_created_issue_count"] == 0
    assert "<h1>Gateway 来源覆盖缺口报告</h1>" in html


def _gateway_probe_payload() -> dict[str, object]:
    return {
        "version": "narrative-source-gateway-probe-v1",
        "generated_at": "2026-06-05T09:00:00+00:00",
        "source_results": [
            {
                "source_kind": "official_filings",
                "status": "completed",
                "row_count": 2,
                "degradation_events": [],
            },
            {
                "source_kind": "official_disclosures",
                "status": "completed",
                "row_count": 1,
                "degradation_events": [],
            },
            {
                "source_kind": "news_context",
                "status": "missing",
                "row_count": 0,
                "degradation_events": [],
            },
            {
                "source_kind": "open_news_index",
                "status": "degraded",
                "row_count": 0,
                "degradation_events": ["REQUEST_TIMEOUT"],
            },
            {
                "source_kind": "social_heat",
                "status": "degraded",
                "row_count": 0,
                "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
            },
        ],
    }
