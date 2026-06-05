from __future__ import annotations

import json

from scripts import run_fresh_narrative_digest, run_narrative_candidate_inbox
from src.product_shell.route_registry import build_product_shell_route_registry
from src.scanners.fresh_narrative_digest import (
    build_fresh_narrative_digest,
    build_narrative_candidate_inbox,
    render_fresh_narrative_digest_html,
    render_narrative_candidate_inbox_html,
)


def test_fresh_narrative_digest_clusters_dedupes_and_assigns_states():
    digest = build_fresh_narrative_digest(
        source_events=_source_events(),
        generated_at="2026-06-02T10:00:00+00:00",
        window_start="2026-06-02T00:00:00+00:00",
        window_end="2026-06-02T23:59:59+00:00",
        fixture_mode=True,
    )

    assert digest["version"] == "fresh-narrative-digest-v1"
    assert digest["status"] == "ok"
    assert digest["contract"]["supported_candidate_states"] == [
        "new",
        "accelerating",
        "persistent",
        "cooling",
        "disputed",
    ]
    assert digest["summary"] == {
        "raw_event_count": 7,
        "deduped_event_count": 6,
        "digest_item_count": 4,
        "degraded_item_count": 1,
    }
    ai = next(item for item in digest["items"] if item["narrative_key"] == "ai-infrastructure")
    assert ai["candidate_state"] == "accelerating"
    assert ai["stable_digest_id"].startswith("NDIG_")
    assert ai["reason_for_inclusion"] == "3 source events in the selected window."
    assert ai["source_quality_metadata"]["best_trust_tier"] == "trusted_fact"
    assert ai["evidence_links"][0]["source_event_id"] == "EVT_AI_1"
    assert ai["entities"]["stocks"][0]["stable_entity_id"] == "STOCK_AAPL"
    disputed = next(item for item in digest["items"] if item["candidate_state"] == "disputed")
    assert disputed["degradation_events"] == ["conflicting_claim"]
    assert digest["entity_resolution_contract"]["ambiguous_entity_policy"] == "keep_candidate_with_alias_context"
    assert digest["dedupe_contract"]["stable_id_inputs"] == [
        "source_event_id",
        "dedupe_key",
        "provider",
        "normalized_title",
        "published_at",
    ]


def test_fresh_narrative_digest_html_is_chinese_and_cites_source_quality():
    html = render_fresh_narrative_digest_html(
        build_fresh_narrative_digest(
            source_events=_source_events(),
            generated_at="2026-06-02T10:00:00+00:00",
            window_start="2026-06-02T00:00:00+00:00",
            window_end="2026-06-02T23:59:59+00:00",
            fixture_mode=True,
        )
    )

    assert "<h1>今日叙事监控摘要</h1>" in html
    assert "AI infrastructure" in html
    assert "来源质量" in html
    assert "不生成交易建议" in html


def test_fresh_narrative_digest_cli_reads_gateway_probe_and_writes_json_html(tmp_path):
    input_path = tmp_path / "gateway_probe.json"
    input_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-02T10:00:00+00:00",
                "fixture_mode": True,
                "source_results": [{"rows": _source_events()}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = run_fresh_narrative_digest.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "digest"),
            "--window-start",
            "2026-06-02T00:00:00+00:00",
            "--window-end",
            "2026-06-02T23:59:59+00:00",
        ]
    )

    payload = json.loads((tmp_path / "digest" / "fresh_narrative_digest.json").read_text())
    html = (tmp_path / "digest" / "fresh_narrative_digest.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["digest_item_count"] == 4
    assert "<h1>今日叙事监控摘要</h1>" in html


def test_fresh_narrative_digest_preserves_gateway_gaps_and_trust_boundaries():
    probe = _gateway_probe_payload()
    digest = build_fresh_narrative_digest(
        source_events=run_fresh_narrative_digest.extract_source_events_from_probe(probe),
        source_results=probe["source_results"],
        generated_at="2026-06-05T10:00:00+00:00",
        window_start="2026-06-05T00:00:00+00:00",
        window_end="2026-06-05T23:59:59+00:00",
        fixture_mode=True,
    )

    assert digest["status"] == "degraded"
    assert digest["summary"]["coverage_gap_count"] == 3
    assert digest["source_coverage"]["expected_source_kinds"] == [
        "official_filings",
        "official_disclosures",
        "official_sources",
        "news_context",
        "open_news_index",
        "industry_media",
        "social_heat",
    ]
    assert {
        gap["source_kind"]: gap["coverage_status"] for gap in digest["source_coverage"]["gaps"]
    } == {
        "official_disclosures": "missing",
        "open_news_index": "degraded",
        "social_heat": "degraded",
    }
    open_news = next(item for item in digest["items"] if item["narrative_key"] == "apple-ai")
    assert open_news["trust_state"] == "context_only"
    assert open_news["source_quality_metadata"]["best_trust_tier"] == "context_only"
    official = next(item for item in digest["items"] if item["narrative_key"] == "us-official-filings")
    assert official["trust_state"] == "trusted_fact"
    assert "degraded_input" in digest["daily_digest_sections"]
    assert digest["daily_digest_sections"]["degraded_input"] == [
        "official_disclosures",
        "open_news_index",
        "social_heat",
    ]


def test_narrative_candidate_inbox_groups_events_without_promoting_trust():
    probe = _gateway_probe_payload()
    inbox = build_narrative_candidate_inbox(
        source_events=run_fresh_narrative_digest.extract_source_events_from_probe(probe),
        source_results=probe["source_results"],
        generated_at="2026-06-05T10:00:00+00:00",
        fixture_mode=True,
    )

    assert inbox["version"] == "narrative-candidate-inbox-v1"
    assert inbox["status"] == "degraded"
    assert inbox["summary"]["candidate_count"] == 3
    assert inbox["summary"]["coverage_gap_count"] == 3
    assert all(candidate["candidate_status"] == "candidate_untrusted" for candidate in inbox["candidates"])
    assert all(candidate["promotion_allowed"] is False for candidate in inbox["candidates"])
    official = next(candidate for candidate in inbox["candidates"] if candidate["narrative_key"] == "us-official-filings")
    assert official["support_class"] == "official_fact_backed"
    assert "仍需人工复核" in official["why_untrusted"]
    heat = next(candidate for candidate in inbox["candidates"] if candidate["narrative_key"] == "retail-heat")
    assert heat["support_class"] == "heat_signal_only"


def test_narrative_candidate_inbox_html_is_chinese():
    html = render_narrative_candidate_inbox_html(
        build_narrative_candidate_inbox(
            source_events=run_fresh_narrative_digest.extract_source_events_from_probe(
                _gateway_probe_payload()
            ),
            source_results=_gateway_probe_payload()["source_results"],
            generated_at="2026-06-05T10:00:00+00:00",
            fixture_mode=True,
        )
    )

    assert "<h1>候选叙事收件箱</h1>" in html
    assert "不会自动升级为可信叙事" in html
    assert "官方事实支撑候选" in html
    assert "热度信号候选" in html


def test_narrative_candidate_inbox_cli_writes_json_html(tmp_path):
    input_path = tmp_path / "gateway_probe.json"
    input_path.write_text(
        json.dumps(_gateway_probe_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_narrative_candidate_inbox.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "candidate_inbox"),
        ]
    )

    payload = json.loads(
        (tmp_path / "candidate_inbox" / "narrative_candidate_inbox.json").read_text()
    )
    html = (
        tmp_path / "candidate_inbox" / "narrative_candidate_inbox.html"
    ).read_text()

    assert exit_code == 0
    assert payload["summary"]["candidate_count"] == 3
    assert "<h1>候选叙事收件箱</h1>" in html


def test_crawler_adapter_contract_is_fixture_safe_and_excludes_browser_rendering():
    digest = build_fresh_narrative_digest(
        source_events=[],
        window_start="2026-06-02T00:00:00+00:00",
        window_end="2026-06-02T23:59:59+00:00",
        fixture_mode=True,
    )
    crawler = digest["crawler_adapter_contract"]

    assert crawler["network_required_for_fixture_tests"] is False
    assert crawler["dynamic_browser_rendering_allowed"] is False
    assert crawler["required_fields"] >= [
        "max_concurrency",
        "per_domain_pacing_seconds",
        "timeout_seconds",
        "retry_backoff_seconds",
        "cache_ttl_seconds",
        "content_hash",
        "parser_version",
        "robots_tos_metadata",
        "failure_reason",
    ]


def test_route_registry_exposes_fresh_narrative_digest_surface():
    registry = build_product_shell_route_registry(
        artifact_index_path="outputs/product_shell/artifact_index.json",
    )
    route = next(route for route in registry["routes"] if route["route_id"] == "fresh_narrative_digest")

    assert route["path"] == "/narratives/digest"
    assert route["data_source"]["type"] == "generated_artifact"
    assert route["data_source"]["json_path"] == (
        "outputs/fresh_narrative_digest/current/fresh_narrative_digest.json"
    )


def _source_events() -> list[dict[str, object]]:
    return [
        _event("EVT_AI_1", "AI chips expand", "AI infrastructure", "AAPL", trust_tier="trusted_fact"),
        _event("EVT_AI_2", "AI chips expand", "AI infrastructure", "NVDA", dedupe_key="same-title"),
        _event("EVT_AI_DUP", "AI chips expand", "AI infrastructure", "NVDA", dedupe_key="same-title"),
        _event("EVT_AI_3", "AI infrastructure order", "AI infrastructure", "MSFT"),
        _event("EVT_SOLAR", "Solar supply update", "Solar demand", "000012"),
        _event("EVT_OLD", "Battery material older update", "Battery material", "300750", event_time="2026-05-28"),
        _event(
            "EVT_DISPUTED",
            "Conflicting tariff claim",
            "Tariff policy",
            "600519",
            degradation_events=["conflicting_claim"],
        ),
    ]


def _event(
    event_id: str,
    title: str,
    narrative: str,
    stock_code: str,
    *,
    trust_tier: str = "context_only",
    dedupe_key: str = "",
    event_time: str = "2026-06-02",
    degradation_events: list[str] | None = None,
) -> dict[str, object]:
    return {
        "source_event_id": event_id,
        "event_id": event_id,
        "title": title,
        "event_time": event_time,
        "published_at": event_time,
        "provider": "gateway_fixture",
        "dedupe_key": dedupe_key,
        "narrative_hints": [narrative],
        "mentioned_stocks": [{"stock_code": stock_code, "stock_name": stock_code}],
        "source_trust_tier": trust_tier,
        "source_quality": {"label": trust_tier},
        "license_scope": "metadata_only",
        "retention_policy": "metadata_and_excerpt",
        "degradation_events": degradation_events or [],
    }


def _gateway_probe_payload() -> dict[str, object]:
    return {
        "generated_at": "2026-06-05T09:00:00+00:00",
        "fixture_mode": True,
        "source_results": [
            {
                "source_kind": "official_filings",
                "status": "completed",
                "row_count": 1,
                "degradation_events": [],
                "rows": [
                    _event(
                        "EVT_OFFICIAL",
                        "Apple 10-K AI infrastructure risk",
                        "US official filings",
                        "AAPL",
                        trust_tier="trusted_fact",
                    )
                    | {"source_kind": "official_filings"}
                ],
            },
            {
                "source_kind": "official_disclosures",
                "status": "missing",
                "row_count": 0,
                "degradation_events": [],
                "rows": [],
            },
            {
                "source_kind": "official_sources",
                "status": "completed",
                "row_count": 1,
                "degradation_events": [],
                "rows": [],
            },
            {
                "source_kind": "news_context",
                "status": "completed",
                "row_count": 1,
                "degradation_events": [],
                "rows": [],
            },
            {
                "source_kind": "open_news_index",
                "status": "degraded",
                "row_count": 1,
                "degradation_events": ["REQUEST_TIMEOUT"],
                "rows": [
                    _event(
                        "EVT_NEWS",
                        "Apple AI supply chain coverage",
                        "Apple AI",
                        "AAPL",
                        trust_tier="trusted_fact",
                    )
                    | {"source_kind": "open_news_index", "degradation_events": ["REQUEST_TIMEOUT"]}
                ],
            },
            {
                "source_kind": "industry_media",
                "status": "completed",
                "row_count": 1,
                "degradation_events": [],
                "rows": [],
            },
            {
                "source_kind": "social_heat",
                "status": "degraded",
                "row_count": 1,
                "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
                "rows": [
                    _event(
                        "EVT_HEAT",
                        "Retail chatter on Apple AI",
                        "Retail heat",
                        "AAPL",
                        trust_tier="trusted_fact",
                    )
                    | {"source_kind": "social_heat", "degradation_events": ["SOCIAL_SOURCE_DISABLED"]}
                ],
            },
        ],
    }
