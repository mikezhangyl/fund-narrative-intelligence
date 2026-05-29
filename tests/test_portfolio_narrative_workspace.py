from __future__ import annotations

import json

from scripts import run_portfolio_narrative_workspace
from src.scanners.portfolio_narrative_workspace import (
    build_portfolio_narrative_workspace,
    render_html_report,
)


def test_portfolio_workspace_builds_watchlists_snapshots_alerts_and_radar_drilldown():
    report = build_portfolio_narrative_workspace(
        payload=_workspace_payload(),
        as_of="2026-05-30T09:30:00+08:00",
    )

    assert report["version"] == "portfolio-narrative-workspace-v1"
    assert report["summary"] == {
        "watchlist_count": 2,
        "snapshot_count": 2,
        "dominant_narrative_count": 2,
        "comparison_count": 2,
        "alert_count": 4,
        "radar_impact_count": 2,
        "validation_warning_count": 1,
    }
    assert report["watchlists"][0]["watchlist_id"] == "wl-core-growth"
    assert report["watchlists"][0]["validation_state"] == "valid"
    assert report["watchlists"][1]["validation_state"] == "degraded"
    assert report["dashboard"]["snapshots"][0]["concentration"]["top_narrative_id"] == (
        "N_AI_INFRA"
    )
    assert report["dashboard"]["snapshots"][0]["quality_breakdown"] == {
        "trusted": 1,
        "candidate": 1,
        "blocked": 0,
    }
    assert report["comparisons"][0]["watchlist_id"] == "wl-core-growth"
    assert report["comparisons"][0]["narrative_deltas"][0]["delta"] == 0.16
    assert {alert["alert_type"] for alert in report["alerts"]} >= {
        "dominant_narrative_added",
        "large_exposure_change",
        "quality_degradation",
        "heating_radar_overlap",
    }
    assert all("buy" not in json.dumps(alert).lower() for alert in report["alerts"])
    assert report["radar_impacts"][0]["narrative_id"] == "N_AI_INFRA"
    assert report["radar_impacts"][0]["affected_watchlist_count"] == 2
    assert report["field_lineage"]["dashboard.snapshots.exposures"]["owner_service"] == (
        "FNI"
    )
    assert report["field_lineage"]["dashboard.snapshots.exposures"]["source_service"] == (
        "Narrative Service"
    )


def test_portfolio_workspace_html_is_chinese_and_discloses_non_advice_boundary():
    report = build_portfolio_narrative_workspace(
        payload=_workspace_payload(),
        as_of="2026-05-30T09:30:00+08:00",
    )

    html = render_html_report(report)

    assert "<h1>组合叙事工作台</h1>" in html
    assert "观察性提醒" in html
    assert "雷达到组合影响" in html
    assert "不构成投资建议" in html
    assert "N_AI_INFRA" in html


def test_run_portfolio_narrative_workspace_writes_json_and_html(tmp_path):
    fixture_path = tmp_path / "workspace.json"
    fixture_path.write_text(
        json.dumps(_workspace_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_portfolio_narrative_workspace.main(
        [
            "--input-path",
            str(fixture_path),
            "--as-of",
            "2026-05-30T09:30:00+08:00",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "portfolio_narrative_workspace.json").read_text())
    html = (tmp_path / "portfolio_narrative_workspace.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["alert_count"] == 4
    assert payload["summary"]["radar_impact_count"] == 2
    assert "<h1>组合叙事工作台</h1>" in html


def _workspace_payload() -> dict:
    return {
        "workspace_id": "ws-demo",
        "workspace_name": "Demo workspace",
        "watchlists": [
            {
                "watchlist_id": "wl-core-growth",
                "name": "核心成长组合",
                "type": "portfolio",
                "notes": "基金和自选股混合观察",
                "instruments": [
                    {"symbol": "161725", "kind": "fund", "weight": 0.6},
                    {"symbol": "512760", "kind": "etf", "weight": 0.4},
                ],
            },
            {
                "watchlist_id": "wl-incomplete",
                "name": "待完善组合",
                "type": "fund_set",
                "instruments": [
                    {"symbol": "515880", "kind": "etf", "weight": 1.0},
                    {"symbol": "", "kind": "fund", "weight": 0.2},
                ],
            },
        ],
        "current_snapshots": [
            _snapshot(
                "wl-core-growth",
                [
                    _exposure("N_AI_INFRA", "AI 基础设施", 0.42, "trusted", "A", 87),
                    _exposure("N_SEMI_CAPEX", "半导体景气", 0.24, "candidate", "B", 72),
                ],
            ),
            _snapshot(
                "wl-incomplete",
                [
                    _exposure("N_AI_INFRA", "AI 基础设施", 0.22, "trusted", "A", 86),
                ],
            ),
        ],
        "previous_snapshots": [
            _snapshot(
                "wl-core-growth",
                [
                    _exposure("N_AI_INFRA", "AI 基础设施", 0.26, "trusted", "A", 88),
                    _exposure("N_OLD_ENERGY", "旧能源", 0.18, "trusted", "A", 84),
                    _exposure("N_SEMI_CAPEX", "半导体景气", 0.22, "trusted", "A", 81),
                ],
            ),
            _snapshot(
                "wl-incomplete",
                [
                    _exposure("N_AI_INFRA", "AI 基础设施", 0.18, "trusted", "A", 86),
                ],
            ),
        ],
        "radar_narratives": [
            {
                "narrative_id": "N_AI_INFRA",
                "narrative_name": "AI 基础设施",
                "heat_score": 91,
                "trend": "heating",
                "evidence_ids": ["EV_AI_001"],
            },
            {
                "narrative_id": "N_ROBOTICS",
                "narrative_name": "机器人",
                "heat_score": 82,
                "trend": "heating",
                "evidence_ids": ["EV_ROBOT_001"],
            },
        ],
    }


def _snapshot(watchlist_id: str, exposures: list[dict]) -> dict:
    return {
        "watchlist_id": watchlist_id,
        "snapshot_id": f"snap-{watchlist_id}",
        "as_of": "2026-05-30T09:00:00+08:00",
        "source_diagnostics": [
            {
                "field": "holdings",
                "source_service": "Gateway",
                "status": "fresh",
            },
            {
                "field": "narrative_quality",
                "source_service": "Narrative Service",
                "status": "fresh",
            },
        ],
        "exposures": exposures,
    }


def _exposure(
    narrative_id: str,
    narrative_name: str,
    exposure: float,
    trust_state: str,
    quality_grade: str,
    quality_score: int,
) -> dict:
    return {
        "narrative_id": narrative_id,
        "narrative_name": narrative_name,
        "raw_exposure": exposure,
        "trust_state": trust_state,
        "quality_grade": quality_grade,
        "quality_score": quality_score,
        "holdings": [
            {
                "symbol": "600519",
                "name": "贵州茅台",
                "weight": 0.08,
                "mapping_quality": "reviewed",
            }
        ],
        "evidence_ids": [f"EV_{narrative_id}_001"],
    }
