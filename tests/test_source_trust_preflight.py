from __future__ import annotations

import copy
import json

from scripts import run_source_trust_preflight
from src.modules.narrative_review.source_trust_preflight import (
    build_source_trust_preflight,
    render_source_trust_preflight_html,
)


def test_source_trust_preflight_passes_official_candidate_with_ready_review_state():
    queue = _queue()
    evidence = _official_evidence()
    ledger = _ledger("CAND_AI", "ready_for_trust_preflight")
    original_inputs = (copy.deepcopy(queue), copy.deepcopy(evidence), copy.deepcopy(ledger))

    preflight = build_source_trust_preflight(
        candidate_id="CAND_AI",
        review_queue=queue,
        evidence_detail=evidence,
        action_ledger=ledger,
        generated_at="2026-06-08T09:40:00Z",
    )

    assert (queue, evidence, ledger) == original_inputs
    assert preflight["version"] == "source-trust-preflight-v1"
    assert preflight["candidate_id"] == "CAND_AI"
    assert preflight["overall_status"] == "pass"
    assert preflight["promotion_allowed"] is False
    assert preflight["read_only"] is True
    assert {criterion["criterion_id"]: criterion["status"] for criterion in preflight["criteria"]} == {
        "official_or_primary_source": "pass",
        "source_diversity": "pass",
        "entity_symbol_clarity": "pass",
        "freshness": "pass",
        "degradation_or_contradiction": "pass",
        "review_action_state": "pass",
        "evidence_metadata": "pass",
    }
    assert all("explanation_zh" in criterion for criterion in preflight["criteria"])


def test_source_trust_preflight_fails_context_and_heat_only_candidates():
    context = build_source_trust_preflight(
        candidate_id="CAND_CONTEXT",
        review_queue=_queue(),
        evidence_detail=_context_evidence(),
        action_ledger=_ledger("CAND_CONTEXT", "ready_for_trust_preflight"),
    )
    heat = build_source_trust_preflight(
        candidate_id="CAND_HEAT",
        review_queue=_queue(),
        evidence_detail=_heat_evidence(),
        action_ledger=_ledger("CAND_HEAT", "ready_for_trust_preflight"),
    )

    assert context["overall_status"] == "fail"
    assert heat["overall_status"] == "fail"
    assert "上下文" in context["blocking_reasons"][0]
    assert "热度" in heat["blocking_reasons"][0]


def test_source_trust_preflight_fails_without_ready_review_action_or_metadata():
    preflight = build_source_trust_preflight(
        candidate_id="CAND_AI",
        review_queue=_queue(),
        evidence_detail=_official_evidence(missing_url=True),
        action_ledger=_ledger("CAND_AI", "watch"),
    )

    statuses = {criterion["criterion_id"]: criterion["status"] for criterion in preflight["criteria"]}
    assert preflight["overall_status"] == "fail"
    assert statuses["review_action_state"] == "fail"
    assert statuses["evidence_metadata"] == "fail"
    assert any("ready_for_trust_preflight" in reason for reason in preflight["blocking_reasons"])


def test_source_trust_preflight_html_is_chinese_and_explains_criteria():
    html = render_source_trust_preflight_html(
        build_source_trust_preflight(
            candidate_id="CAND_AI",
            review_queue=_queue(),
            evidence_detail=_official_evidence(),
            action_ledger=_ledger("CAND_AI", "ready_for_trust_preflight"),
        )
    )

    assert "<h1>候选叙事信任预检</h1>" in html
    assert "官方或主来源" in html
    assert "来源多样性" in html
    assert "不会自动升级" in html
    assert "不构成投资建议" in html


def test_source_trust_preflight_cli_writes_candidate_named_artifacts(tmp_path):
    queue_path = tmp_path / "queue.json"
    evidence_path = tmp_path / "evidence.json"
    ledger_path = tmp_path / "ledger.json"
    queue_path.write_text(json.dumps(_queue(), ensure_ascii=False), encoding="utf-8")
    evidence_path.write_text(json.dumps(_official_evidence(), ensure_ascii=False), encoding="utf-8")
    ledger_path.write_text(
        json.dumps(_ledger("CAND_AI", "ready_for_trust_preflight"), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_source_trust_preflight.main(
        [
            "--queue",
            str(queue_path),
            "--evidence",
            str(evidence_path),
            "--ledger",
            str(ledger_path),
            "--candidate-id",
            "CAND_AI",
            "--output-dir",
            str(tmp_path / "preflight"),
        ]
    )

    payload = json.loads((tmp_path / "preflight" / "CAND_AI.json").read_text())
    html = (tmp_path / "preflight" / "CAND_AI.html").read_text()

    assert exit_code == 0
    assert payload["overall_status"] == "pass"
    assert "<h1>候选叙事信任预检</h1>" in html


def _queue() -> dict[str, object]:
    return {
        "version": "source-candidate-review-queue-v1",
        "rows": [
            _queue_row("CAND_AI", "official_fact_backed", ["AAPL", "NVDA"], "accelerating"),
            _queue_row("CAND_CONTEXT", "context_only", ["688012.SH"], "new"),
            _queue_row("CAND_HEAT", "heat_signal_only", ["AAPL"], "disputed"),
        ],
    }


def _queue_row(
    candidate_id: str,
    support_class: str,
    symbols: list[str],
    freshness_state: str,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": candidate_id,
        "candidate_state": "candidate_untrusted",
        "freshness_state": freshness_state,
        "related_entities": {"symbols": symbols, "markets": ["US"]},
        "trust_tier_summary": {
            "support_class": support_class,
            "best_trust_tier": "trusted_fact" if support_class == "official_fact_backed" else support_class,
        },
        "degradation_flags": [],
        "trusted_promotion_allowed": False,
    }


def _official_evidence(*, missing_url: bool = False) -> dict[str, object]:
    return {
        "version": "candidate-evidence-detail-v1",
        "candidate": {"candidate_id": "CAND_AI", "freshness_state": "accelerating"},
        "summary": {"missing_event_count": 0, "degraded_event_count": 0},
        "events": [
            _event("EVT_OFFICIAL", "official_filings", "trusted_fact", missing_url=missing_url),
            _event("EVT_DISCLOSURE", "official_disclosures", "trusted_fact"),
        ],
    }


def _context_evidence() -> dict[str, object]:
    return {
        "version": "candidate-evidence-detail-v1",
        "candidate": {"candidate_id": "CAND_CONTEXT", "freshness_state": "new"},
        "summary": {"missing_event_count": 0, "degraded_event_count": 0},
        "events": [_event("EVT_CONTEXT", "news_context", "context_only")],
    }


def _heat_evidence() -> dict[str, object]:
    return {
        "version": "candidate-evidence-detail-v1",
        "candidate": {"candidate_id": "CAND_HEAT", "freshness_state": "disputed"},
        "summary": {"missing_event_count": 0, "degraded_event_count": 1},
        "events": [_event("EVT_HEAT", "social_heat", "heat_signal_only", degraded=True)],
    }


def _event(
    event_id: str,
    source_kind: str,
    trust_tier: str,
    *,
    missing_url: bool = False,
    degraded: bool = False,
) -> dict[str, object]:
    return {
        "source_event_id": event_id,
        "event_status": "degraded" if degraded else "available",
        "source_kind": source_kind,
        "trust_tier": trust_tier,
        "source_url": "" if missing_url else f"https://example.com/{event_id}",
        "event_time": "2026-06-08T01:00:00Z",
        "source_quality": "trusted_fact_candidate" if trust_tier == "trusted_fact" else trust_tier,
        "degradation_events": ["REQUEST_TIMEOUT"] if degraded else [],
    }


def _ledger(candidate_id: str, state: str) -> dict[str, object]:
    return {
        "version": "source-candidate-review-action-ledger-v1",
        "records": [
            {
                "action_id": f"ACT_{candidate_id}",
                "candidate_id": candidate_id,
                "action": state,
                "new_candidate_state": state,
                "created_at": "2026-06-08T09:30:00Z",
                "trusted_promotion_allowed": False,
            }
        ],
    }
