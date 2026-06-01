from __future__ import annotations

import json

from scripts import run_historical_replay
from src.scanners.historical_replay_runner import (
    build_historical_replay_run,
    render_historical_replay_html,
)


def test_historical_replay_run_is_deterministic_bounded_and_non_trading():
    replay = build_historical_replay_run(
        replay_input=_replay_input(),
        artifacts=_artifacts(),
        generated_at="2026-06-02T06:00:00+08:00",
    )

    assert replay["version"] == "historical-replay-run-v1"
    assert replay["replay_input"]["window"] == {
        "start_date": "2026-06-01",
        "end_date": "2026-06-02",
    }
    assert replay["run"]["run_id"].startswith("replay_")
    assert replay["run"]["deterministic"] is True
    assert replay["run"]["bounded"] is True
    assert replay["run"]["resumable"] is True
    assert replay["contract"] == {
        "provider_access_allowed": False,
        "trading_backtest_allowed": False,
        "return_prediction_allowed": False,
        "metrics_scope": "system_quality_only",
    }
    assert replay["summary"] == {
        "input_artifact_count": 4,
        "source_event_count": 2,
        "radar_snapshot_count": 2,
        "quality_finding_count": 1,
        "portfolio_alert_count": 1,
        "warning_count": 0,
    }
    assert replay["output_manifest"]["formula_versions"] == {
        "radar_heat": "radar-heat-v1",
        "quality": "quality-v1",
    }
    assert "alpha" not in json.dumps(replay, ensure_ascii=False).lower()
    assert "buy" not in json.dumps(replay, ensure_ascii=False).lower()


def test_historical_replay_html_is_chinese_and_discloses_evaluation_boundary():
    html = render_historical_replay_html(
        build_historical_replay_run(
            replay_input=_replay_input(),
            artifacts=_artifacts(),
        )
    )

    assert "<h1>历史回放与评估运行</h1>" in html
    assert "不是交易回测" in html
    assert "EVT-1" in html
    assert "alert-v1" in html


def test_historical_replay_cli_reads_spec_and_artifacts_then_writes_json_html(tmp_path):
    spec_path = tmp_path / "replay_input.json"
    timeline_path = tmp_path / "timeline.json"
    digest_path = tmp_path / "digest.json"
    quality_path = tmp_path / "quality.json"
    portfolio_path = tmp_path / "portfolio.json"
    output_dir = tmp_path / "replay"
    spec = _replay_input()
    spec["artifacts"] = {
        "source_events": str(timeline_path),
        "radar_snapshots": str(digest_path),
        "quality": str(quality_path),
        "portfolio_alerts": str(portfolio_path),
    }
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    timeline_path.write_text(json.dumps(_artifacts()["source_events"], ensure_ascii=False), encoding="utf-8")
    digest_path.write_text(json.dumps(_artifacts()["radar_snapshots"], ensure_ascii=False), encoding="utf-8")
    quality_path.write_text(json.dumps(_artifacts()["quality"], ensure_ascii=False), encoding="utf-8")
    portfolio_path.write_text(json.dumps(_artifacts()["portfolio_alerts"], ensure_ascii=False), encoding="utf-8")

    exit_code = run_historical_replay.main(
        ["--input", str(spec_path), "--output-dir", str(output_dir)]
    )

    payload = json.loads((output_dir / "historical_replay_run.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["source_event_count"] == 2
    assert "<h1>历史回放与评估运行</h1>" in (
        output_dir / "historical_replay_run.html"
    ).read_text()


def _replay_input() -> dict[str, object]:
    return {
        "version": "historical-replay-input-v1",
        "window": {"start_date": "2026-06-01", "end_date": "2026-06-02"},
        "source_mode": "artifact",
        "formula_versions": {
            "radar_heat": "radar-heat-v1",
            "quality": "quality-v1",
        },
        "bounds": {"max_source_events": 10, "max_alerts": 10},
        "resume": {"checkpoint_id": "ckpt-empty", "completed_steps": []},
        "artifacts": {
            "source_events": "timeline.json",
            "radar_snapshots": "digest.json",
            "quality": "quality.json",
            "portfolio_alerts": "portfolio.json",
        },
    }


def _artifacts() -> dict[str, dict[str, object]]:
    return {
        "source_events": {
            "results": [
                {
                    "source_event_id": "EVT-1",
                    "published_at": "2026-06-01T09:00:00+08:00",
                    "title": "AI filing",
                    "quality_state": "trusted_fact",
                },
                {
                    "source_event_id": "EVT-2",
                    "published_at": "2026-06-02T09:00:00+08:00",
                    "title": "算力公告",
                    "quality_state": "trusted_fact",
                },
                {
                    "source_event_id": "EVT-OLD",
                    "published_at": "2026-05-20T09:00:00+08:00",
                    "title": "out of window",
                    "quality_state": "context_only",
                },
            ]
        },
        "radar_snapshots": {
            "items": [
                {"stable_digest_id": "RADAR-1", "display_name": "AI", "event_count": 2},
                {"stable_digest_id": "RADAR-2", "display_name": "算力", "event_count": 1},
            ]
        },
        "quality": {
            "findings": [
                {
                    "issue_code": "LOW_SOURCE_DIVERSITY",
                    "narrative_id": "N_AI",
                    "quality_score": 79.2,
                }
            ]
        },
        "portfolio_alerts": {
            "alerts": [
                {
                    "rule_id": "alert-v1",
                    "alert_type": "large_exposure_change",
                    "narrative_name": "AI",
                    "delta": 0.16,
                }
            ]
        },
    }
