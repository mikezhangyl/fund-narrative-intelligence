from __future__ import annotations

import json

from scripts import run_fresh_narrative_digest
from src.product_shell.route_registry import build_product_shell_route_registry
from src.scanners.fresh_narrative_digest import (
    build_fresh_narrative_digest,
    render_fresh_narrative_digest_html,
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
