from __future__ import annotations

import json

from scripts import run_source_operator_workflow
from src.modules.narrative_review.source_operator_workflow import (
    build_source_operator_workflow,
    render_source_operator_workflow_html,
)


def test_source_operator_workflow_links_digest_to_queue_and_evidence():
    workflow = build_source_operator_workflow(
        fresh_digest=_digest(),
        review_queue=_queue(),
        preflight_index=_preflight_index(),
        generated_at="2026-06-08T10:00:00Z",
    )

    assert workflow["version"] == "source-operator-workflow-v1"
    assert workflow["summary"] == {
        "digest_item_count": 4,
        "linked_candidate_count": 3,
        "degraded_input_count": 1,
        "trusted_item_count": 0,
    }
    official = workflow["items"][0]
    assert official["digest_item_id"] == "NDIG_AI"
    assert official["candidate_id"] == "CAND_AI"
    assert official["candidate_state"] == "candidate_untrusted"
    assert official["next_operator_action"] == "run_trust_preflight"
    assert official["artifact_links"] == {
        "queue_html": "source_candidate_review_queue.html#CAND_AI",
        "evidence_detail_html": "candidate_evidence/CAND_AI.html",
        "trust_preflight_html": "source_trust_preflight/CAND_AI.html",
    }
    assert official["source_trust_label"] == "trusted_fact"
    assert official["degradation_flags"] == []
    degraded = next(item for item in workflow["items"] if item["digest_item_id"] == "NDIG_DEGRADED")
    assert degraded["candidate_id"] == ""
    assert degraded["input_state"] == "degraded"
    assert degraded["next_operator_action"] == "request_more_evidence"
    assert "GATEWAY_SOURCE_KIND_MISSING" in degraded["degradation_flags"]
    assert all(item["trusted_implied"] is False for item in workflow["items"])


def test_source_operator_workflow_recommends_watch_for_heat_and_inspect_for_context():
    workflow = build_source_operator_workflow(
        fresh_digest=_digest(),
        review_queue=_queue(),
        preflight_index={},
    )

    by_candidate = {item["candidate_id"]: item for item in workflow["items"] if item["candidate_id"]}
    assert by_candidate["CAND_CONTEXT"]["next_operator_action"] == "inspect_evidence"
    assert by_candidate["CAND_HEAT"]["next_operator_action"] == "watch"


def test_source_operator_workflow_html_is_chinese_and_cross_link_readable():
    html = render_source_operator_workflow_html(
        build_source_operator_workflow(
            fresh_digest=_digest(),
            review_queue=_queue(),
            preflight_index=_preflight_index(),
        )
    )

    assert "<h1>每日摘要到候选复核工作流</h1>" in html
    assert "不会暗示可信叙事" in html
    assert "source_candidate_review_queue.html#CAND_AI" in html
    assert "candidate_evidence/CAND_AI.html" in html
    assert "source_trust_preflight/CAND_AI.html" in html
    assert "GATEWAY_SOURCE_KIND_MISSING" in html


def test_source_operator_workflow_cli_writes_json_and_html(tmp_path):
    digest_path = tmp_path / "fresh_narrative_digest.json"
    queue_path = tmp_path / "source_candidate_review_queue.json"
    preflight_path = tmp_path / "preflight_index.json"
    digest_path.write_text(json.dumps(_digest(), ensure_ascii=False), encoding="utf-8")
    queue_path.write_text(json.dumps(_queue(), ensure_ascii=False), encoding="utf-8")
    preflight_path.write_text(json.dumps(_preflight_index(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_source_operator_workflow.main(
        [
            "--digest",
            str(digest_path),
            "--queue",
            str(queue_path),
            "--preflight-index",
            str(preflight_path),
            "--output-dir",
            str(tmp_path / "workflow"),
        ]
    )

    payload = json.loads((tmp_path / "workflow" / "source_operator_workflow.json").read_text())
    html = (tmp_path / "workflow" / "source_operator_workflow.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["linked_candidate_count"] == 3
    assert "<h1>每日摘要到候选复核工作流</h1>" in html


def _digest() -> dict[str, object]:
    return {
        "version": "fresh-narrative-digest-v1",
        "items": [
            {
                "stable_digest_id": "NDIG_AI",
                "narrative_key": "ai-infrastructure",
                "display_name": "AI infrastructure",
                "candidate_state": "accelerating",
                "source_quality_metadata": {"best_trust_tier": "trusted_fact"},
                "degradation_events": [],
            },
            {
                "stable_digest_id": "NDIG_CONTEXT",
                "narrative_key": "semiconductor-equipment",
                "display_name": "半导体设备",
                "candidate_state": "new",
                "source_quality_metadata": {"best_trust_tier": "context_only"},
                "degradation_events": [],
            },
            {
                "stable_digest_id": "NDIG_HEAT",
                "narrative_key": "retail-heat",
                "display_name": "Retail heat",
                "candidate_state": "disputed",
                "source_quality_metadata": {"best_trust_tier": "heat_signal_only"},
                "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
            },
            {
                "stable_digest_id": "NDIG_DEGRADED",
                "narrative_key": "missing-input",
                "display_name": "Missing input",
                "candidate_state": "disputed",
                "source_quality_metadata": {"best_trust_tier": "candidate_untrusted"},
                "degradation_events": ["GATEWAY_SOURCE_KIND_MISSING"],
            },
        ],
        "source_coverage": {
            "gaps": [
                {
                    "source_kind": "official_sources",
                    "coverage_status": "missing",
                    "degradation_events": ["GATEWAY_SOURCE_KIND_MISSING"],
                }
            ]
        },
    }


def _queue() -> dict[str, object]:
    return {
        "version": "source-candidate-review-queue-v1",
        "rows": [
            _queue_row("CAND_AI", "ai-infrastructure", "official_fact_backed", "trusted_fact"),
            _queue_row("CAND_CONTEXT", "semiconductor-equipment", "context_only", "context_only"),
            _queue_row("CAND_HEAT", "retail-heat", "heat_signal_only", "heat_signal_only"),
        ],
    }


def _queue_row(
    candidate_id: str,
    topic: str,
    support_class: str,
    trust_tier: str,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": topic,
        "topic": topic,
        "candidate_state": "candidate_untrusted",
        "trust_tier_summary": {
            "support_class": support_class,
            "best_trust_tier": trust_tier,
        },
        "degradation_flags": ["SOCIAL_SOURCE_DISABLED"] if support_class == "heat_signal_only" else [],
        "artifact_links": {
            "evidence_detail_html": f"candidate_evidence/{candidate_id}.html",
            "evidence_detail_json": f"candidate_evidence/{candidate_id}.json",
        },
    }


def _preflight_index() -> dict[str, object]:
    return {
        "CAND_AI": {
            "overall_status": "warning",
            "artifact_links": {
                "html": "source_trust_preflight/CAND_AI.html",
                "json": "source_trust_preflight/CAND_AI.json",
            },
        }
    }
