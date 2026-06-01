from __future__ import annotations

import json

from scripts import run_narrative_evidence_graph
from src.scanners.narrative_evidence_graph import (
    build_narrative_evidence_graph,
    render_narrative_evidence_graph_html,
)


def test_evidence_graph_builds_supported_nodes_edges_and_comparison_metrics():
    graph = build_narrative_evidence_graph(
        source_events=_source_events(),
        narratives=["AI", "算力"],
        generated_at="2026-06-02T04:00:00+08:00",
    )

    assert graph["version"] == "narrative-evidence-graph-v1"
    assert graph["summary"] == {
        "narrative_count": 2,
        "event_count": 2,
        "node_count": 7,
        "edge_count": 10,
        "unsupported_inference_count": 0,
    }
    assert graph["contract"]["unsupported_inferred_links_allowed"] is False
    assert graph["contract"]["provider_access_allowed"] is False
    assert {node["node_id"] for node in graph["nodes"]} >= {
        "NARRATIVE_AI",
        "NARRATIVE_算力",
        "EVENT_EVT-1",
        "STOCK_000063",
        "SECTOR_通信",
        "CONCEPT_算力",
    }
    assert {
        (edge["from_node_id"], edge["to_node_id"], edge["edge_type"])
        for edge in graph["edges"]
    } >= {
        ("NARRATIVE_AI", "EVENT_EVT-1", "supported_by_event"),
        ("EVENT_EVT-1", "STOCK_000063", "mentions_stock"),
        ("EVENT_EVT-1", "SECTOR_通信", "mentions_sector"),
        ("EVENT_EVT-1", "CONCEPT_算力", "mentions_concept"),
    }
    assert graph["comparisons"][0]["narratives"] == ["AI", "算力"]
    assert graph["comparisons"][0]["shared_source_event_ids"] == ["EVT-1", "EVT-3"]
    assert graph["comparisons"][0]["shared_tickers"] == ["000063"]
    assert graph["comparisons"][0]["contradictions"] == [
        {
            "source_event_id": "EVT-3",
            "reason": "degraded source event cannot support trusted comparison",
        }
    ]


def test_evidence_graph_html_is_chinese_and_discloses_no_invention_policy():
    html = render_narrative_evidence_graph_html(
        build_narrative_evidence_graph(
            source_events=_source_events(),
            narratives=["AI", "算力"],
        )
    )

    assert "<h1>叙事比较与证据图谱</h1>" in html
    assert "不创建无证据推断边" in html
    assert "EVT-1" in html
    assert "共享事件" in html


def test_evidence_graph_cli_reads_timeline_search_and_writes_json_html(tmp_path):
    input_path = tmp_path / "timeline.json"
    output_dir = tmp_path / "graph"
    input_path.write_text(
        json.dumps({"results": _source_events()}, ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_narrative_evidence_graph.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--narrative",
            "AI",
            "--narrative",
            "算力",
        ]
    )

    payload = json.loads((output_dir / "narrative_evidence_graph.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["narrative_count"] == 2
    assert "<h1>叙事比较与证据图谱</h1>" in (
        output_dir / "narrative_evidence_graph.html"
    ).read_text()


def _source_events() -> list[dict[str, object]]:
    return [
        {
            "source_event_id": "EVT-1",
            "published_at": "2026-06-02T09:30:00+08:00",
            "title": "AI 算力订单公告",
            "source_id": "sec_edgar",
            "source_type": "official_disclosure",
            "quality_state": "trusted_fact",
            "entities": {
                "narratives": ["AI", "算力"],
                "tickers": ["000063"],
                "sectors": ["通信"],
                "concepts": ["算力"],
            },
            "citations": {
                "source_event_id": "EVT-1",
                "evidence_url": "https://example.com/evt-1",
            },
        },
        {
            "source_event_id": "EVT-2",
            "published_at": "2026-06-01T10:00:00+08:00",
            "title": "白酒渠道调研",
            "source_id": "news",
            "source_type": "news_context",
            "quality_state": "context_only",
            "entities": {
                "narratives": ["消费"],
                "tickers": ["600519"],
                "sectors": ["食品饮料"],
                "concepts": ["白酒"],
            },
            "citations": {
                "source_event_id": "EVT-2",
                "evidence_url": "https://example.com/evt-2",
            },
        },
        {
            "source_event_id": "EVT-3",
            "published_at": "2026-06-02T11:00:00+08:00",
            "title": "社交热度禁用",
            "source_id": "stocktwits",
            "source_type": "social_heat",
            "quality_state": "heat_signal_only",
            "entities": {
                "narratives": ["AI", "算力"],
                "tickers": ["000063"],
                "sectors": ["通信"],
                "concepts": ["算力"],
            },
            "citations": {
                "source_event_id": "EVT-3",
                "evidence_url": "https://example.com/evt-3",
            },
            "degradation_status": "degraded",
        },
    ]
