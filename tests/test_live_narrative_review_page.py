from __future__ import annotations

import json

from scripts import run_live_narrative_review_page
from src.modules.narrative_review.live_review_page import (
    build_live_narrative_review_page,
    render_live_narrative_review_page_html,
)


def test_live_narrative_review_page_exposes_real_gateway_titles_urls_and_actions():
    page = build_live_narrative_review_page(
        topic_results=[
            _topic_result(
                topic_name="AI infrastructure",
                source_results=[
                    _source_result(
                        "official_filings",
                        rows=[
                            _source_row(
                                source_event_id="EVT_AI_OFFICIAL",
                                title="NVIDIA 10-Q mentions AI infrastructure demand",
                                source_url="https://www.sec.gov/Archives/edgar/data/1045810/sample.htm",
                                source_kind="official_filings",
                                trust_tier="trusted_fact",
                                source_quality="trusted_fact_candidate",
                            )
                        ],
                    ),
                    _source_result(
                        "news_context",
                        rows=[
                            _source_row(
                                source_event_id="EVT_AI_NEWS",
                                title="Cloud capex rises on AI infrastructure buildout",
                                source_url="https://example.com/cloud-ai-capex",
                                source_kind="news_context",
                                trust_tier="context_only",
                                source_quality="context_only",
                            )
                        ],
                    ),
                    _source_result("social_heat", status="degraded", rows=[]),
                ],
            ),
            _topic_result(
                topic_name="solar/storage",
                source_results=[
                    _source_result("official_filings", status="missing", rows=[]),
                    _source_result(
                        "industry_media",
                        status="degraded",
                        rows=[],
                        degradation_events=[{"code": "NO_ROWS", "message": "No rows returned"}],
                    ),
                ],
            ),
        ],
        generated_at="2026-06-08T12:30:00+00:00",
        base_url="http://127.0.0.1:8700",
        fixture_mode=True,
    )

    assert page["version"] == "live-narrative-review-page-v1"
    assert page["summary"] == {
        "topic_count": 2,
        "candidate_count": 1,
        "source_event_count": 2,
        "missing_source_kind_count": 1,
        "degraded_source_kind_count": 2,
    }
    assert page["contract"] == {
        "gateway_only_source_access": True,
        "trusted_promotion_allowed": False,
        "investment_signal_allowed": False,
        "llm_narrative_generation_allowed": False,
    }

    ai_topic = page["topics"][0]
    assert ai_topic["status"] == "candidate_available"
    assert ai_topic["candidate"]["candidate_name"] == "AI infrastructure"
    assert "Gateway 返回 2 条来源事件" in ai_topic["candidate"]["summary"]
    assert ai_topic["candidate"]["candidate_state"] == "candidate_untrusted"
    assert ai_topic["candidate"]["next_operator_action"] == "inspect_evidence"
    assert ai_topic["candidate"]["trusted_promotion_allowed"] is False
    assert [event["title"] for event in ai_topic["evidence_events"]] == [
        "NVIDIA 10-Q mentions AI infrastructure demand",
        "Cloud capex rises on AI infrastructure buildout",
    ]
    assert ai_topic["evidence_events"][0]["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/1045810/sample.htm"
    )
    assert ai_topic["source_kind_states"]["social_heat"]["status"] == "degraded"

    solar_topic = page["topics"][1]
    assert solar_topic["status"] == "no_usable_rows"
    assert solar_topic["candidate"] is None
    assert solar_topic["missing_or_degraded_source_kinds"] == [
        {
            "source_kind": "official_filings",
            "status": "missing",
            "row_count": 0,
            "reason": "NO_ROWS",
        },
        {
            "source_kind": "industry_media",
            "status": "degraded",
            "row_count": 0,
            "reason": "NO_ROWS",
        },
    ]


def test_live_narrative_review_page_html_is_chinese_visible_and_non_promotional():
    html = render_live_narrative_review_page_html(
        build_live_narrative_review_page(
            topic_results=[
                _topic_result(
                    topic_name="AI infrastructure",
                    source_results=[
                        _source_result(
                            "official_filings",
                            rows=[
                                _source_row(
                                    title="NVIDIA 10-Q mentions AI infrastructure demand",
                                    source_url="https://www.sec.gov/Archives/edgar/data/1045810/sample.htm",
                                )
                            ],
                        )
                    ],
                ),
                _topic_result(
                    topic_name="solar/storage",
                    source_results=[
                        _source_result("industry_media", status="degraded", rows=[]),
                    ],
                ),
            ]
        )
    )

    assert "<h1>真实叙事复核页</h1>" in html
    assert "AI infrastructure" in html
    assert "NVIDIA 10-Q mentions AI infrastructure demand" in html
    assert "https://www.sec.gov/Archives/edgar/data/1045810/sample.htm" in html
    assert "source kind" not in html.lower()
    assert "来源类型" in html
    assert "信任层级" in html
    assert "来源质量" in html
    assert "缺口状态" in html
    assert "solar/storage" in html
    assert "不提供投资建议" in html
    assert "不会自动升级为可信叙事" in html


def test_live_narrative_review_page_cli_writes_fixture_json_and_chinese_html(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "AI infrastructure": {
                    "official_filings": {
                        "data": {
                            "rows": [
                                _gateway_row(
                                    source_event_id="EVT_AI_OFFICIAL",
                                    title="NVIDIA 10-Q mentions AI infrastructure demand",
                                    source_url="https://www.sec.gov/Archives/edgar/data/1045810/sample.htm",
                                )
                            ]
                        },
                        "meta": {"owner_service": "stock-data-gateway"},
                    }
                },
                "solar/storage": {
                    "industry_media": {
                        "data": {"rows": []},
                        "meta": {
                            "status": "degraded",
                            "degradation_events": [
                                {"code": "NO_ROWS", "message": "No matching rows"}
                            ],
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = run_live_narrative_review_page.main(
        [
            "--base-url",
            "http://127.0.0.1:8700",
            "--fixture-json",
            str(fixture_path),
            "--source-kind",
            "official_filings",
            "--source-kind",
            "industry_media",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    payload = json.loads((tmp_path / "out" / "live_narrative_review_page.json").read_text())
    html = (tmp_path / "out" / "live_narrative_review_page.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["candidate_count"] == 1
    assert payload["topics"][0]["evidence_events"][0]["source_url"].startswith("https://www.sec.gov/")
    assert "<h1>真实叙事复核页</h1>" in html
    assert "NVIDIA 10-Q mentions AI infrastructure demand" in html
    assert "缺口状态" in html


def _topic_result(topic_name: str, source_results: list[dict[str, object]]) -> dict[str, object]:
    return {
        "topic_name": topic_name,
        "query": topic_name,
        "source_results": source_results,
    }


def _source_result(
    source_kind: str,
    *,
    status: str = "completed",
    rows: list[dict[str, object]] | None = None,
    degradation_events: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "source_kind": source_kind,
        "status": status,
        "row_count": len(rows or []),
        "rows": rows or [],
        "degradation_events": degradation_events or [],
    }


def _source_row(**overrides: object) -> dict[str, object]:
    row = {
        "source_event_id": "EVT_AI_OFFICIAL",
        "event_id": "EVT_AI_OFFICIAL",
        "source_kind": "official_filings",
        "title": "NVIDIA 10-Q mentions AI infrastructure demand",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/sample.htm",
        "event_time": "2026-06-08T10:00:00Z",
        "provider": "gateway_sec_edgar",
        "source_provider": "sec_edgar",
        "trust_tier": "trusted_fact",
        "source_quality": "trusted_fact_candidate",
        "retention_policy": "metadata_and_permitted_excerpt",
        "license_scope": "metadata_and_public_filing_reference",
        "metadata_only": True,
        "degradation_events": [],
    }
    return {**row, **overrides}


def _gateway_row(**overrides: object) -> dict[str, object]:
    row = {
        "source_event_id": "EVT_AI_OFFICIAL",
        "source_type": "filing",
        "source_provider": "sec_edgar",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/sample.htm",
        "title": "NVIDIA 10-Q mentions AI infrastructure demand",
        "event_time": "2026-06-08T10:00:00Z",
        "fetched_at": "2026-06-08T10:01:00Z",
        "trust_tier": "trusted_fact",
        "source_quality": "trusted_fact_candidate",
        "license_scope": "metadata_and_public_filing_reference",
        "retention_policy": "metadata_and_permitted_excerpt",
        "metadata_only": True,
        "degradation_events": [],
        "summary": "Official filing sample",
        "stock_codes": ["NVDA"],
        "narrative_hints": ["AI infrastructure"],
    }
    return {**row, **overrides}
