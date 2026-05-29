from __future__ import annotations

import json
from pathlib import Path

from scripts import run_fund_narrative_change_monitor
from src.scanners.fund_narrative_change_monitor import (
    build_fund_narrative_change_report,
    render_html_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_fund_narrative_change_report_classifies_exposure_changes():
    payload = _snapshot_payload()

    report = build_fund_narrative_change_report(
        previous_snapshot=payload["previous_snapshot"],
        current_snapshot=payload["current_snapshot"],
    )

    assert report["version"] == "fund-narrative-change-monitor-v1"
    assert report["status"] == "partial"
    assert report["fund"]["fund_code"] == "000001"
    assert report["summary"] == {
        "added_count": 1,
        "removed_count": 1,
        "increased_count": 1,
        "decreased_count": 1,
        "concentration_change_count": 1,
        "data_gap_count": 1,
    }
    assert report["added_narratives"][0]["narrative_id"] == "N_AI_INFRA"
    assert report["removed_narratives"][0]["narrative_id"] == "N_SEMI_CAPEX"
    assert report["increased_narratives"][0]["delta"] == 0.18
    assert report["decreased_narratives"][0]["delta"] == -0.08
    assert report["concentration_changes"][0]["narrative_id"] == "N_BAIJIU_CONSUMPTION"
    assert report["source_disclosure"]["holding_source"]["provider"] == "mock-fixture-provider"
    assert report["source_disclosure"]["mapping_trust_state"] == "untrusted_experimental"
    assert "buy" not in json.dumps(report, ensure_ascii=False).lower()
    assert "sell" not in json.dumps(report, ensure_ascii=False).lower()


def test_fund_narrative_change_monitor_html_is_chinese_and_discloses_no_advice():
    payload = _snapshot_payload()
    report = build_fund_narrative_change_report(
        previous_snapshot=payload["previous_snapshot"],
        current_snapshot=payload["current_snapshot"],
    )

    html = render_html_report(report)

    assert "<h1>基金叙事变化监控报告</h1>" in html
    assert "新增叙事" in html
    assert "淡出叙事" in html
    assert "暴露上升" in html
    assert "暴露下降" in html
    assert "数据缺口" in html
    assert "不构成投资建议" in html


def test_run_fund_narrative_change_monitor_writes_json_and_html(tmp_path):
    snapshot_path = tmp_path / "snapshots.json"
    snapshot_path.write_text(json.dumps(_snapshot_payload(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_fund_narrative_change_monitor.main(
        [
            "--snapshots-path",
            str(snapshot_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "fund_narrative_change_monitor_report.json").read_text())
    html = (tmp_path / "fund_narrative_change_monitor_report.html").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["summary"]["added_count"] == 1
    assert payload["summary"]["removed_count"] == 1
    assert "基金叙事变化监控报告" in html


def _snapshot_payload() -> dict:
    return json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "narrative_change_snapshots.v1.json")
        .read_text(encoding="utf-8")
    )
