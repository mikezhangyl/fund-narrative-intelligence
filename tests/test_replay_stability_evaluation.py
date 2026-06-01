from __future__ import annotations

import json

from scripts import run_replay_stability_evaluation
from src.scanners.replay_stability_evaluation import (
    build_replay_stability_evaluation,
    render_replay_stability_evaluation_html,
)


def test_stability_evaluation_reports_system_quality_metrics_without_trading_claims():
    evaluation = build_replay_stability_evaluation(
        replay_run=_replay_run(),
        generated_at="2026-06-02T06:30:00+08:00",
    )

    assert evaluation["version"] == "replay-stability-evaluation-v1"
    assert evaluation["summary"] == {
        "radar_snapshot_count": 3,
        "quality_finding_count": 2,
        "source_event_count": 4,
        "stale_source_event_count": 1,
        "metric_count": 4,
        "warning_count": 0,
    }
    assert evaluation["contract"] == {
        "metrics_scope": "system_quality_only",
        "trading_backtest_allowed": False,
        "return_prediction_allowed": False,
        "portfolio_optimization_allowed": False,
    }
    metric_ids = [metric["metric_id"] for metric in evaluation["metrics"]]
    assert metric_ids == [
        "radar_event_count_variability",
        "quality_issue_density",
        "source_freshness_coverage",
        "formula_version_coverage",
    ]
    assert evaluation["metrics"][0]["value"] == 6
    serialized = json.dumps(evaluation, ensure_ascii=False).lower()
    assert "alpha" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized


def test_stability_evaluation_html_is_chinese_and_explains_metric_scope():
    html = render_replay_stability_evaluation_html(
        build_replay_stability_evaluation(replay_run=_replay_run())
    )

    assert "<h1>雷达与质量稳定性评估</h1>" in html
    assert "系统质量指标" in html
    assert "radar_event_count_variability" in html


def test_stability_evaluation_cli_reads_replay_and_writes_json_html(tmp_path):
    replay_path = tmp_path / "replay.json"
    output_dir = tmp_path / "evaluation"
    replay_path.write_text(json.dumps(_replay_run(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_replay_stability_evaluation.main(
        ["--replay", str(replay_path), "--output-dir", str(output_dir)]
    )

    payload = json.loads((output_dir / "replay_stability_evaluation.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["metric_count"] == 4
    assert "<h1>雷达与质量稳定性评估</h1>" in (
        output_dir / "replay_stability_evaluation.html"
    ).read_text()


def _replay_run() -> dict[str, object]:
    return {
        "version": "historical-replay-run-v1",
        "replay_input": {
            "window": {"start_date": "2026-05-08", "end_date": "2026-06-02"},
            "formula_versions": {
                "radar_heat": "fresh-narrative-digest-v1",
                "quality": "narrative-quality-audit-v1",
            },
        },
        "source_events": [
            {"source_event_id": "EVT-1", "published_at": "2026-06-02"},
            {"source_event_id": "EVT-2", "published_at": "2026-06-01"},
            {"source_event_id": "EVT-3", "published_at": "2026-05-29"},
            {"source_event_id": "EVT-4", "published_at": "2026-05-08"},
        ],
        "radar_snapshots": [
            {"snapshot_id": "R1", "display_name": "AI", "event_count": 7},
            {"snapshot_id": "R2", "display_name": "算力", "event_count": 1},
            {"snapshot_id": "R3", "display_name": "股东会", "event_count": 2},
        ],
        "quality_findings": [
            {"issue_code": "LOW_SOURCE_DIVERSITY", "quality_score": 79.2},
            {"issue_code": "LOW_EXTRACTION_CONFIDENCE", "quality_score": 72.0},
        ],
        "output_manifest": {
            "formula_versions": {
                "radar_heat": "fresh-narrative-digest-v1",
                "quality": "narrative-quality-audit-v1",
            }
        },
    }
