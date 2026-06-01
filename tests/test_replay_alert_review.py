from __future__ import annotations

import json

from scripts import run_replay_alert_review
from src.scanners.replay_alert_review import (
    build_replay_alert_review,
    render_replay_alert_review_html,
)


def test_alert_review_flags_repeated_noise_and_storage_contract():
    review = build_replay_alert_review(
        replay_run=_replay_run(),
        generated_at="2026-06-02T07:00:00+08:00",
    )

    assert review["version"] == "replay-alert-review-v1"
    assert review["summary"] == {
        "alert_count": 3,
        "repeated_trigger_count": 1,
        "disabled_threshold_candidate_count": 1,
        "missed_change_candidate_count": 0,
        "warning_count": 0,
    }
    assert review["job_storage_contract"] == {
        "status_values": ["pending", "running", "completed", "failed", "resumable"],
        "stores_progress": True,
        "stores_resume_metadata": True,
        "stores_failure_reason": True,
        "current_production_state_mutation_allowed": False,
    }
    assert review["noise_reviews"][0]["recommendation"] == "review_threshold"
    serialized = json.dumps(review, ensure_ascii=False).lower()
    assert "system-quality feedback" in serialized
    assert "alpha" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized


def test_alert_review_html_is_chinese():
    html = render_replay_alert_review_html(
        build_replay_alert_review(replay_run=_replay_run())
    )

    assert "<h1>历史告警有效性与噪声复盘</h1>" in html
    assert "系统质量反馈" in html
    assert "large_exposure_change-v1" in html


def test_alert_review_cli_reads_replay_and_writes_json_html(tmp_path):
    replay_path = tmp_path / "replay.json"
    output_dir = tmp_path / "review"
    replay_path.write_text(json.dumps(_replay_run(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_replay_alert_review.main(
        ["--replay", str(replay_path), "--output-dir", str(output_dir)]
    )

    payload = json.loads((output_dir / "replay_alert_review.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["alert_count"] == 3
    assert "<h1>历史告警有效性与噪声复盘</h1>" in (
        output_dir / "replay_alert_review.html"
    ).read_text()


def _replay_run() -> dict[str, object]:
    return {
        "version": "historical-replay-run-v1",
        "run": {
            "run_id": "replay-test",
            "status": "completed",
            "resume_metadata": {"checkpoint_id": "ckpt-1"},
        },
        "portfolio_alerts": [
            {
                "rule_id": "large_exposure_change-v1",
                "alert_type": "large_exposure_change",
                "narrative_name": "AI",
                "delta": 0.16,
            },
            {
                "rule_id": "large_exposure_change-v1",
                "alert_type": "large_exposure_change",
                "narrative_name": "AI",
                "delta": 0.04,
            },
            {
                "rule_id": "dominant_narrative_added-v1",
                "alert_type": "dominant_narrative_added",
                "narrative_name": "AI",
                "delta": 0.15,
            },
        ],
        "warnings": [],
        "output_manifest": {
            "generated_artifacts": ["historical_replay_run.json", "historical_replay_run.html"]
        },
    }
