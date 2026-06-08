from __future__ import annotations

import json

import pytest
from scripts import run_source_review_action_ledger
from src.modules.narrative_review.source_action_ledger import (
    append_candidate_review_action,
    build_empty_review_action_ledger,
    render_review_action_ledger_html,
)


@pytest.mark.parametrize(
    ("action", "new_state"),
    [
        ("watch", "watching"),
        ("needs_more_evidence", "needs_more_evidence"),
        ("reject", "rejected"),
        ("defer", "deferred"),
        ("ready_for_trust_preflight", "ready_for_trust_preflight"),
    ],
)
def test_source_review_action_ledger_records_supported_actions(action, new_state):
    ledger = append_candidate_review_action(
        ledger=build_empty_review_action_ledger(generated_at="2026-06-08T09:20:00Z"),
        review_queue=_review_queue(),
        action_request={
            "candidate_id": "CAND_AI",
            "action": action,
            "reason": f"Reason for {action}",
            "actor": "reviewer-placeholder",
            "idempotency_key": f"idem-{action}",
            "created_at": "2026-06-08T09:21:00Z",
            "source_artifact_refs": {
                "queue": "outputs/source_candidate_review_queue/current/source_candidate_review_queue.json",
                "evidence_detail": "outputs/candidate_evidence/current/CAND_AI.json",
            },
        },
    )

    record = ledger["records"][0]
    assert ledger["version"] == "source-candidate-review-action-ledger-v1"
    assert ledger["summary"]["total_action_count"] == 1
    assert ledger["summary"]["trusted_action_count"] == 0
    assert record["action_id"].startswith("ACT_CAND_AI_")
    assert record["candidate_id"] == "CAND_AI"
    assert record["actor"] == "reviewer-placeholder"
    assert record["action"] == action
    assert record["reason"] == f"Reason for {action}"
    assert record["previous_candidate_state"] == "candidate_untrusted"
    assert record["new_candidate_state"] == new_state
    assert record["trusted_promotion_allowed"] is False
    assert record["source_artifact_refs"]["evidence_detail"].endswith("CAND_AI.json")


def test_source_review_action_ledger_is_append_only_and_idempotent():
    base = build_empty_review_action_ledger(generated_at="2026-06-08T09:20:00Z")
    first = append_candidate_review_action(
        ledger=base,
        review_queue=_review_queue(),
        action_request=_action("watch", idempotency_key="same-key"),
    )
    second = append_candidate_review_action(
        ledger=first,
        review_queue=_review_queue(),
        action_request=_action("watch", idempotency_key="same-key"),
    )
    third = append_candidate_review_action(
        ledger=second,
        review_queue=_review_queue(),
        action_request=_action("needs_more_evidence", idempotency_key="next-key"),
    )

    assert base["records"] == []
    assert len(first["records"]) == 1
    assert second["records"] == first["records"]
    assert second["summary"]["idempotent_replay_count"] == 1
    assert len(third["records"]) == 2
    assert third["records"][1]["previous_candidate_state"] == "watching"
    assert third["records"][1]["new_candidate_state"] == "needs_more_evidence"


def test_source_review_action_ledger_rejects_invalid_action_and_terminal_transition():
    with pytest.raises(ValueError, match="unsupported review action"):
        append_candidate_review_action(
            ledger=build_empty_review_action_ledger(),
            review_queue=_review_queue(),
            action_request=_action("trusted"),
        )

    rejected = append_candidate_review_action(
        ledger=build_empty_review_action_ledger(),
        review_queue=_review_queue(),
        action_request=_action("reject", idempotency_key="reject-key"),
    )
    with pytest.raises(ValueError, match="terminal rejected"):
        append_candidate_review_action(
            ledger=rejected,
            review_queue=_review_queue(),
            action_request=_action("watch", idempotency_key="after-reject"),
        )


def test_source_review_action_ledger_html_is_chinese_summary():
    ledger = append_candidate_review_action(
        ledger=build_empty_review_action_ledger(),
        review_queue=_review_queue(),
        action_request=_action("ready_for_trust_preflight"),
    )
    html = render_review_action_ledger_html(ledger)

    assert "<h1>候选叙事复核动作流水</h1>" in html
    assert "追加写入" in html
    assert "不会直接标记为可信叙事" in html
    assert "ready_for_trust_preflight" in html
    assert "CAND_AI" in html


def test_source_review_action_ledger_cli_writes_json_and_html(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(_review_queue(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_source_review_action_ledger.main(
        [
            "--ledger",
            str(ledger_path),
            "--queue",
            str(queue_path),
            "--candidate-id",
            "CAND_AI",
            "--action",
            "watch",
            "--reason",
            "先观察官方来源后续。",
            "--idempotency-key",
            "cli-key",
            "--output-dir",
            str(tmp_path / "ledger_out"),
        ]
    )

    payload = json.loads(
        (tmp_path / "ledger_out" / "source_review_action_ledger.json").read_text()
    )
    html = (tmp_path / "ledger_out" / "source_review_action_ledger.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["total_action_count"] == 1
    assert payload["records"][0]["action"] == "watch"
    assert ledger_path.exists()
    assert "<h1>候选叙事复核动作流水</h1>" in html


def _action(action: str, *, idempotency_key: str = "idem-key") -> dict[str, object]:
    return {
        "candidate_id": "CAND_AI",
        "action": action,
        "reason": "Needs review.",
        "actor": "reviewer-placeholder",
        "idempotency_key": idempotency_key,
        "created_at": "2026-06-08T09:21:00Z",
        "source_artifact_refs": {
            "queue": "outputs/source_candidate_review_queue/current/source_candidate_review_queue.json",
            "evidence_detail": "outputs/candidate_evidence/current/CAND_AI.json",
        },
    }


def _review_queue() -> dict[str, object]:
    return {
        "version": "source-candidate-review-queue-v1",
        "rows": [
            {
                "candidate_id": "CAND_AI",
                "title": "AI infrastructure",
                "candidate_state": "candidate_untrusted",
                "trust_tier_summary": {
                    "support_class": "official_fact_backed",
                    "best_trust_tier": "trusted_fact",
                },
                "artifact_links": {
                    "evidence_detail_json": "candidate_evidence/CAND_AI.json",
                    "evidence_detail_html": "candidate_evidence/CAND_AI.html",
                },
            }
        ],
    }
