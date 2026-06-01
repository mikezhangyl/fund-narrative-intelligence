from __future__ import annotations

import json

from scripts import run_narrative_timeline_search
from src.scanners.narrative_timeline_search import (
    build_narrative_timeline_search,
    render_narrative_timeline_search_html,
)


def test_timeline_search_filters_by_narrative_ticker_sector_concept_and_quality():
    payload = build_narrative_timeline_search(
        source_events=_source_events(),
        query={
            "narrative": "AI",
            "ticker": "000063",
            "sector": "通信",
            "concept": "算力",
            "source_type": "official_disclosure",
            "freshness": "today",
            "quality_state": "trusted_fact",
        },
        generated_at="2026-06-02T03:30:00+08:00",
    )

    assert payload["version"] == "narrative-timeline-search-v1"
    assert payload["summary"] == {
        "raw_event_count": 3,
        "matched_event_count": 1,
        "returned_event_count": 1,
        "degraded_source_count": 1,
    }
    result = payload["results"][0]
    assert result["source_event_id"] == "EVT-1"
    assert result["timeline_bucket"] == "2026-06-02"
    assert result["citations"] == {
        "source_id": "sec_edgar",
        "source_event_id": "EVT-1",
        "evidence_id": "EVT-1",
        "evidence_url": "https://example.com/evt-1",
    }
    assert result["entities"]["tickers"] == ["000063"]
    assert result["filters_matched"]["quality_state"] == "trusted_fact"
    assert payload["contract"]["provider_access_allowed"] is False
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 50,
        "total": 1,
        "has_next_page": False,
    }


def test_timeline_search_paginates_and_exposes_degraded_source_semantics():
    payload = build_narrative_timeline_search(
        source_events=_source_events(),
        query={"page": 1, "page_size": 1},
    )

    assert payload["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total": 3,
        "has_next_page": True,
    }
    assert len(payload["results"]) == 1
    assert payload["degraded_sources"] == [
        {
            "source_event_id": "EVT-3",
            "source_id": "stocktwits",
            "degradation_status": "degraded",
            "degradation_reason": "SOCIAL_SOURCE_DISABLED",
        }
    ]


def test_timeline_search_html_is_chinese_and_links_evidence():
    html = render_narrative_timeline_search_html(
        build_narrative_timeline_search(
            source_events=_source_events(),
            query={"ticker": "000063"},
        )
    )

    assert "<h1>叙事时间线与来源事件搜索</h1>" in html
    assert "证据链接" in html
    assert "https://example.com/evt-1" in html
    assert "不直接访问 Provider" in html


def test_timeline_search_cli_reads_gateway_probe_and_writes_json_html(tmp_path):
    input_path = tmp_path / "probe.json"
    output_dir = tmp_path / "timeline"
    input_path.write_text(
        json.dumps({"source_results": [{"rows": _source_events()}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_narrative_timeline_search.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--ticker",
            "000063",
            "--quality-state",
            "trusted_fact",
        ]
    )

    payload = json.loads((output_dir / "narrative_timeline_search.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["matched_event_count"] == 1
    assert "<h1>叙事时间线与来源事件搜索</h1>" in (
        output_dir / "narrative_timeline_search.html"
    ).read_text()


def _source_events() -> list[dict[str, object]]:
    return [
        {
            "source_event_id": "EVT-1",
            "published_at": "2026-06-02T09:30:00+08:00",
            "title": "AI 算力订单公告",
            "provider": "sec_edgar",
            "source_kind": "official_disclosure",
            "narrative_hints": ["AI", "算力"],
            "stock_codes": ["000063"],
            "sectors": ["通信"],
            "concepts": ["算力"],
            "quality_state": "trusted_fact",
            "trust_tier": "trusted_fact",
            "url": "https://example.com/evt-1",
        },
        {
            "source_event_id": "EVT-2",
            "published_at": "2026-06-01T10:00:00+08:00",
            "title": "白酒渠道调研",
            "provider": "news",
            "source_kind": "news_context",
            "narrative_hints": ["消费"],
            "stock_codes": ["600519"],
            "sectors": ["食品饮料"],
            "concepts": ["白酒"],
            "quality_state": "context_only",
            "url": "https://example.com/evt-2",
        },
        {
            "source_event_id": "EVT-3",
            "published_at": "2026-06-02T11:00:00+08:00",
            "title": "社交热度禁用",
            "provider": "stocktwits",
            "source_kind": "social_heat",
            "narrative_hints": ["AI"],
            "stock_codes": ["000063"],
            "sectors": ["通信"],
            "concepts": ["算力"],
            "quality_state": "heat_signal_only",
            "degradation_status": "degraded",
            "degradation_reason": "SOCIAL_SOURCE_DISABLED",
            "url": "https://example.com/evt-3",
        },
    ]
