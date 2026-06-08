from __future__ import annotations

import json

from scripts import run_source_candidate_review_queue
from src.modules.narrative_review.source_queue import (
    build_source_candidate_review_queue,
    render_source_candidate_review_queue_html,
)


def test_source_candidate_review_queue_builds_required_rows_without_trust_promotion():
    queue = build_source_candidate_review_queue(
        candidate_inbox=_candidate_inbox(),
        fresh_digest=_fresh_digest(),
        generated_at="2026-06-08T08:40:00+00:00",
    )

    assert queue["version"] == "source-candidate-review-queue-v1"
    assert queue["summary"] == {
        "total_count": 3,
        "visible_count": 3,
        "official_backed_count": 1,
        "context_only_count": 1,
        "heat_only_count": 1,
        "degraded_count": 1,
        "trusted_count": 0,
    }
    official = next(row for row in queue["rows"] if row["candidate_id"] == "CAND_OFFICIAL")
    assert official["candidate_id"] == "CAND_OFFICIAL"
    assert official["title"] == "AI infrastructure"
    assert official["candidate_state"] == "candidate_untrusted"
    assert official["freshness_state"] == "accelerating"
    assert official["source_event_count"] == 2
    assert official["source_kind_mix"] == [
        {"source_kind": "official_filings", "event_count": 1},
        {"source_kind": "news_context", "event_count": 1},
    ]
    assert official["newest_event_time"] == "2026-06-08T03:00:00Z"
    assert official["related_entities"] == {
        "symbols": ["AAPL", "NVDA"],
        "markets": ["US"],
    }
    assert official["trust_tier_summary"] == {
        "best_trust_tier": "trusted_fact",
        "source_quality_labels": ["trusted_fact_candidate", "context_only"],
        "support_class": "official_fact_backed",
    }
    assert official["degradation_flags"] == []
    assert official["review_priority"] == "high"
    assert official["trusted_promotion_allowed"] is False
    assert official["artifact_links"]["evidence_detail_html"] == (
        "candidate_evidence/CAND_OFFICIAL.html"
    )
    assert all(row["candidate_state"] != "trusted" for row in queue["rows"])
    assert all(row["trusted_promotion_allowed"] is False for row in queue["rows"])


def test_source_candidate_review_queue_filters_by_source_trust_freshness_market_and_state():
    queue = build_source_candidate_review_queue(
        candidate_inbox=_candidate_inbox(),
        fresh_digest=_fresh_digest(),
        filters={
            "source_kind": "social_heat",
            "trust_tier": "heat_signal_only",
            "freshness_state": "disputed",
            "market": "US",
            "candidate_state": "candidate_untrusted",
        },
    )

    assert queue["summary"]["total_count"] == 3
    assert queue["summary"]["visible_count"] == 1
    assert queue["filters"] == {
        "source_kind": "social_heat",
        "trust_tier": "heat_signal_only",
        "freshness_state": "disputed",
        "market": "US",
        "candidate_state": "candidate_untrusted",
    }
    assert queue["rows"][0]["candidate_id"] == "CAND_HEAT"
    assert queue["rows"][0]["review_priority"] == "needs_triage"


def test_source_candidate_review_queue_html_is_chinese_and_separates_support_classes():
    html = render_source_candidate_review_queue_html(
        build_source_candidate_review_queue(
            candidate_inbox=_candidate_inbox(),
            fresh_digest=_fresh_digest(),
        )
    )

    assert "<h1>来源候选叙事复核队列</h1>" in html
    assert "不会自动升级为可信叙事" in html
    assert "官方事实支撑候选" in html
    assert "上下文候选" in html
    assert "热度信号候选" in html
    assert "candidate_evidence/CAND_OFFICIAL.html" in html
    assert "投资建议" in html


def test_source_candidate_review_queue_cli_writes_json_and_html(tmp_path):
    inbox_path = tmp_path / "narrative_candidate_inbox.json"
    digest_path = tmp_path / "fresh_narrative_digest.json"
    inbox_path.write_text(json.dumps(_candidate_inbox(), ensure_ascii=False), encoding="utf-8")
    digest_path.write_text(json.dumps(_fresh_digest(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_source_candidate_review_queue.main(
        [
            "--inbox",
            str(inbox_path),
            "--digest",
            str(digest_path),
            "--output-dir",
            str(tmp_path / "queue"),
            "--source-kind",
            "official_filings",
        ]
    )

    payload = json.loads(
        (tmp_path / "queue" / "source_candidate_review_queue.json").read_text()
    )
    html = (tmp_path / "queue" / "source_candidate_review_queue.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["visible_count"] == 1
    assert payload["rows"][0]["candidate_id"] == "CAND_OFFICIAL"
    assert "<h1>来源候选叙事复核队列</h1>" in html


def _candidate_inbox() -> dict[str, object]:
    return {
        "version": "narrative-candidate-inbox-v1",
        "generated_at": "2026-06-08T08:30:00+00:00",
        "status": "ok",
        "fixture_mode": True,
        "summary": {"candidate_count": 3},
        "candidates": [
            {
                "stable_candidate_id": "CAND_OFFICIAL",
                "narrative_key": "ai-infrastructure",
                "display_name": "AI infrastructure",
                "candidate_status": "candidate_untrusted",
                "support_class": "official_fact_backed",
                "event_count": 2,
                "source_mix": [
                    {"source_kind": "official_filings", "event_count": 1},
                    {"source_kind": "news_context", "event_count": 1},
                ],
                "newest_event_time": "2026-06-08T03:00:00Z",
                "trust_labels": ["trusted_fact_candidate", "context_only"],
                "trust_state": "candidate_untrusted",
                "promotion_allowed": False,
                "evidence_links": [
                    {
                        "source_event_id": "EVT_OFFICIAL",
                        "title": "Apple filing",
                        "provider": "gateway_sec_edgar",
                        "event_time": "2026-06-08T01:00:00Z",
                    }
                ],
                "source_quality_metadata": {
                    "best_trust_tier": "trusted_fact",
                    "source_quality_labels": [
                        "trusted_fact_candidate",
                        "context_only",
                    ],
                },
                "degradation_events": [],
            },
            {
                "stable_candidate_id": "CAND_CONTEXT",
                "narrative_key": "semiconductor-equipment",
                "display_name": "半导体设备",
                "candidate_status": "candidate_untrusted",
                "support_class": "context_only",
                "event_count": 1,
                "source_mix": [{"source_kind": "news_context", "event_count": 1}],
                "newest_event_time": "2026-06-08T02:00:00Z",
                "trust_labels": ["context_only"],
                "trust_state": "candidate_untrusted",
                "promotion_allowed": False,
                "evidence_links": [],
                "source_quality_metadata": {
                    "best_trust_tier": "context_only",
                    "source_quality_labels": ["context_only"],
                },
                "degradation_events": [],
            },
            {
                "stable_candidate_id": "CAND_HEAT",
                "narrative_key": "retail-heat",
                "display_name": "Retail heat",
                "candidate_status": "candidate_untrusted",
                "support_class": "heat_signal_only",
                "event_count": 1,
                "source_mix": [{"source_kind": "social_heat", "event_count": 1}],
                "newest_event_time": "2026-06-08T01:30:00Z",
                "trust_labels": ["heat_signal_only"],
                "trust_state": "candidate_untrusted",
                "promotion_allowed": False,
                "evidence_links": [],
                "source_quality_metadata": {
                    "best_trust_tier": "heat_signal_only",
                    "source_quality_labels": ["heat_signal_only"],
                },
                "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
            },
        ],
    }


def _fresh_digest() -> dict[str, object]:
    return {
        "version": "fresh-narrative-digest-v1",
        "items": [
            {
                "stable_digest_id": "NDIG_OFFICIAL",
                "narrative_key": "ai-infrastructure",
                "candidate_state": "accelerating",
                "entities": {
                    "stocks": [
                        {"stock_code": "AAPL", "display_name": "Apple"},
                        {"stock_code": "NVDA", "display_name": "NVIDIA"},
                    ]
                },
            },
            {
                "stable_digest_id": "NDIG_CONTEXT",
                "narrative_key": "semiconductor-equipment",
                "candidate_state": "new",
                "entities": {
                    "stocks": [
                        {"stock_code": "688012.SH", "display_name": "中微公司"}
                    ]
                },
            },
            {
                "stable_digest_id": "NDIG_HEAT",
                "narrative_key": "retail-heat",
                "candidate_state": "disputed",
                "entities": {
                    "stocks": [
                        {"stock_code": "AAPL", "display_name": "Apple"}
                    ]
                },
            },
        ],
    }
