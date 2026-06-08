from __future__ import annotations

import json

from scripts import run_candidate_evidence_detail
from src.modules.narrative_review.source_evidence import (
    build_candidate_evidence_detail,
    render_candidate_evidence_detail_html,
)


def test_candidate_evidence_detail_groups_source_events_without_inventing_facts():
    detail = build_candidate_evidence_detail(
        candidate_id="CAND_AI",
        review_queue=_review_queue(),
        source_payload=_source_payload(),
        generated_at="2026-06-08T09:00:00+00:00",
    )

    assert detail["version"] == "candidate-evidence-detail-v1"
    assert detail["candidate"]["candidate_id"] == "CAND_AI"
    assert detail["candidate"]["candidate_state"] == "candidate_untrusted"
    assert detail["trust_promotion_allowed"] is False
    assert detail["summary"] == {
        "source_event_count": 3,
        "visible_event_count": 3,
        "missing_event_count": 1,
        "degraded_event_count": 1,
        "official_event_count": 1,
        "context_or_heat_event_count": 1,
    }
    assert detail["groups"][0]["source_kind"] == "official_filings"
    assert detail["groups"][0]["trust_tier"] == "trusted_fact"
    official = detail["groups"][0]["events"][0]
    assert official["source_event_id"] == "EVT_OFFICIAL"
    assert official["source_url"] == "https://www.sec.gov/Archives/sample.htm"
    assert official["domain"] == "www.sec.gov"
    assert official["source_quality"] == "trusted_fact_candidate"
    assert official["retention_status"] == "metadata_and_permitted_excerpt"
    assert official["extraction_status"] == "metadata_only"
    assert official["freshness_state"] == "accelerating"
    missing = next(event for event in detail["events"] if event["source_event_id"] == "EVT_MISSING")
    assert missing["event_status"] == "missing"
    assert missing["degradation_events"] == ["SOURCE_EVENT_NOT_FOUND"]
    degraded = next(event for event in detail["events"] if event["source_event_id"] == "EVT_NEWS")
    assert degraded["event_status"] == "degraded"
    assert degraded["promotion_evidence_role"] == "context_only_insufficient"
    assert "官方或主来源证据" in detail["promotion_requirements"][0]


def test_candidate_evidence_detail_labels_heat_only_as_insufficient():
    detail = build_candidate_evidence_detail(
        candidate_id="CAND_HEAT",
        review_queue=_review_queue(),
        source_payload=_source_payload(),
    )

    assert detail["candidate"]["support_class"] == "heat_signal_only"
    assert detail["events"][0]["promotion_evidence_role"] == "heat_signal_only_insufficient"
    assert "热度信号不能单独升级" in detail["why_untrusted"]


def test_candidate_evidence_detail_html_is_chinese_and_keeps_degraded_rows_visible():
    html = render_candidate_evidence_detail_html(
        build_candidate_evidence_detail(
            candidate_id="CAND_AI",
            review_queue=_review_queue(),
            source_payload=_source_payload(),
        )
    )

    assert "<h1>候选叙事证据详情</h1>" in html
    assert "仍未升级为可信叙事" in html
    assert "上下文证据不足以单独升级" in html
    assert "SOURCE_EVENT_NOT_FOUND" in html
    assert "https://www.sec.gov/Archives/sample.htm" in html


def test_candidate_evidence_detail_cli_writes_candidate_named_artifacts(tmp_path):
    queue_path = tmp_path / "source_candidate_review_queue.json"
    source_path = tmp_path / "source_payload.json"
    queue_path.write_text(json.dumps(_review_queue(), ensure_ascii=False), encoding="utf-8")
    source_path.write_text(json.dumps(_source_payload(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_candidate_evidence_detail.main(
        [
            "--queue",
            str(queue_path),
            "--source-events",
            str(source_path),
            "--candidate-id",
            "CAND_AI",
            "--output-dir",
            str(tmp_path / "candidate_evidence"),
        ]
    )

    payload = json.loads((tmp_path / "candidate_evidence" / "CAND_AI.json").read_text())
    html = (tmp_path / "candidate_evidence" / "CAND_AI.html").read_text()

    assert exit_code == 0
    assert payload["candidate"]["candidate_id"] == "CAND_AI"
    assert payload["summary"]["missing_event_count"] == 1
    assert "<h1>候选叙事证据详情</h1>" in html


def _review_queue() -> dict[str, object]:
    return {
        "version": "source-candidate-review-queue-v1",
        "rows": [
            {
                "candidate_id": "CAND_AI",
                "title": "AI infrastructure",
                "topic": "ai-infrastructure",
                "candidate_state": "candidate_untrusted",
                "freshness_state": "accelerating",
                "source_event_count": 3,
                "source_kind_mix": [
                    {"source_kind": "official_filings", "event_count": 1},
                    {"source_kind": "news_context", "event_count": 1},
                ],
                "trust_tier_summary": {
                    "best_trust_tier": "trusted_fact",
                    "source_quality_labels": [
                        "trusted_fact_candidate",
                        "context_only",
                    ],
                    "support_class": "official_fact_backed",
                },
                "degradation_flags": [],
                "review_priority": "high",
                "trusted_promotion_allowed": False,
                "artifact_links": {
                    "evidence_detail_json": "candidate_evidence/CAND_AI.json",
                    "evidence_detail_html": "candidate_evidence/CAND_AI.html",
                },
                "evidence_links": [
                    {"source_event_id": "EVT_OFFICIAL", "title": "Apple filing"},
                    {"source_event_id": "EVT_NEWS", "title": "Apple news"},
                    {"source_event_id": "EVT_MISSING", "title": "Missing event"},
                ],
            },
            {
                "candidate_id": "CAND_HEAT",
                "title": "Retail heat",
                "topic": "retail-heat",
                "candidate_state": "candidate_untrusted",
                "freshness_state": "disputed",
                "source_event_count": 1,
                "source_kind_mix": [{"source_kind": "social_heat", "event_count": 1}],
                "trust_tier_summary": {
                    "best_trust_tier": "heat_signal_only",
                    "source_quality_labels": ["heat_signal_only"],
                    "support_class": "heat_signal_only",
                },
                "degradation_flags": ["SOCIAL_SOURCE_DISABLED"],
                "review_priority": "needs_triage",
                "trusted_promotion_allowed": False,
                "artifact_links": {
                    "evidence_detail_json": "candidate_evidence/CAND_HEAT.json",
                    "evidence_detail_html": "candidate_evidence/CAND_HEAT.html",
                },
                "evidence_links": [
                    {"source_event_id": "EVT_HEAT", "title": "Retail heat"},
                ],
            },
        ],
    }


def _source_payload() -> dict[str, object]:
    return {
        "source_results": [
            {
                "source_kind": "official_filings",
                "status": "completed",
                "rows": [
                    {
                        "source_event_id": "EVT_OFFICIAL",
                        "event_id": "EVT_OFFICIAL",
                        "source_kind": "official_filings",
                        "title": "Apple filing",
                        "source_url": "https://www.sec.gov/Archives/sample.htm",
                        "event_time": "2026-06-08T01:00:00Z",
                        "provider": "gateway_sec_edgar",
                        "source_provider": "sec_edgar",
                        "trust_tier": "trusted_fact",
                        "source_quality": "trusted_fact_candidate",
                        "retention_policy": "metadata_and_permitted_excerpt",
                        "metadata_only": True,
                        "degradation_events": [],
                    }
                ],
            },
            {
                "source_kind": "news_context",
                "status": "degraded",
                "degradation_events": ["REQUEST_TIMEOUT"],
                "rows": [
                    {
                        "source_event_id": "EVT_NEWS",
                        "event_id": "EVT_NEWS",
                        "source_kind": "news_context",
                        "title": "Apple news",
                        "source_url": "https://example.com/apple-ai",
                        "event_time": "2026-06-08T02:00:00Z",
                        "provider": "gateway_news",
                        "trust_tier": "context_only",
                        "source_quality": "context_only",
                        "retention_policy": "metadata_only",
                        "metadata_only": True,
                        "degradation_events": ["REQUEST_TIMEOUT"],
                    }
                ],
            },
            {
                "source_kind": "social_heat",
                "status": "degraded",
                "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
                "rows": [
                    {
                        "source_event_id": "EVT_HEAT",
                        "event_id": "EVT_HEAT",
                        "source_kind": "social_heat",
                        "title": "Retail heat",
                        "source_url": "https://stocktwits.com/symbol/AAPL",
                        "event_time": "2026-06-08T03:00:00Z",
                        "provider": "gateway_stocktwits",
                        "trust_tier": "heat_signal_only",
                        "source_quality": "heat_signal_only",
                        "retention_policy": "metadata_only",
                        "metadata_only": True,
                        "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
                    }
                ],
            },
        ]
    }
