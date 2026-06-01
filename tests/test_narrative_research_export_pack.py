from __future__ import annotations

import json

from scripts import run_narrative_research_export_pack
from src.scanners.narrative_research_export_pack import (
    build_narrative_research_export_pack,
    render_narrative_research_export_pack_html,
)


def test_research_export_pack_links_notes_without_promoting_trust_state():
    pack = build_narrative_research_export_pack(
        timeline_search=_timeline_payload(),
        evidence_graph=_graph_payload(),
        analyst_notes=_analyst_notes(),
        generated_at="2026-06-02T05:00:00+08:00",
    )

    assert pack["version"] == "narrative-research-export-pack-v1"
    assert pack["summary"] == {
        "narrative_count": 2,
        "source_event_count": 2,
        "note_count": 2,
        "citation_count": 2,
        "comparison_count": 1,
    }
    assert pack["contract"] == {
        "provider_access_allowed": False,
        "notes_promote_trusted_state": False,
        "citation_required_for_export_items": True,
        "auditable_user_artifacts": True,
    }
    assert pack["analyst_notes"][0]["linked_object_ref"] == {
        "object_type": "narrative",
        "object_id": "AI",
    }
    assert pack["analyst_notes"][0]["promotion_effect"] == "none"
    assert "requested_trust_state" not in pack["analyst_notes"][0]
    assert "trusted_fact" not in json.dumps(pack["analyst_notes"], ensure_ascii=False)
    assert pack["export_manifest"]["citation_ids"] == ["CITE_EVT-1", "CITE_EVT-2"]
    assert pack["export_manifest"]["linked_object_refs"] == [
        {"object_id": "AI", "object_type": "narrative"},
        {"object_id": "EVT-2", "object_type": "source_event"},
    ]


def test_research_export_pack_html_is_chinese_and_exposes_citations():
    html = render_narrative_research_export_pack_html(
        build_narrative_research_export_pack(
            timeline_search=_timeline_payload(),
            evidence_graph=_graph_payload(),
            analyst_notes=_analyst_notes(),
        )
    )

    assert "<h1>研究导出包与分析师笔记</h1>" in html
    assert "笔记不会提升可信状态" in html
    assert "CITE_EVT-1" in html
    assert "AI infrastructure" in html


def test_research_export_pack_cli_reads_current_artifacts_and_writes_json_html(tmp_path):
    timeline_path = tmp_path / "timeline.json"
    graph_path = tmp_path / "graph.json"
    notes_path = tmp_path / "notes.json"
    output_dir = tmp_path / "export"
    timeline_path.write_text(json.dumps(_timeline_payload(), ensure_ascii=False), encoding="utf-8")
    graph_path.write_text(json.dumps(_graph_payload(), ensure_ascii=False), encoding="utf-8")
    notes_path.write_text(json.dumps({"notes": _analyst_notes()}, ensure_ascii=False), encoding="utf-8")

    exit_code = run_narrative_research_export_pack.main(
        [
            "--timeline",
            str(timeline_path),
            "--evidence-graph",
            str(graph_path),
            "--notes",
            str(notes_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    payload = json.loads((output_dir / "narrative_research_export_pack.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["note_count"] == 2
    assert "<h1>研究导出包与分析师笔记</h1>" in (
        output_dir / "narrative_research_export_pack.html"
    ).read_text()


def _timeline_payload() -> dict[str, object]:
    return {
        "version": "narrative-timeline-search-v1",
        "results": [
            {
                "source_event_id": "EVT-1",
                "timeline_bucket": "2026-06-02",
                "published_at": "2026-06-02T09:30:00+08:00",
                "title": "AI infrastructure capex filing",
                "source_id": "sec_edgar",
                "source_type": "filing",
                "quality_state": "trusted_fact",
                "entities": {
                    "narratives": ["AI"],
                    "tickers": ["AAPL"],
                    "sectors": ["Technology"],
                    "concepts": ["AI infrastructure"],
                },
                "citations": {
                    "source_id": "sec_edgar",
                    "source_event_id": "EVT-1",
                    "evidence_id": "EVT-1",
                    "evidence_url": "https://example.com/evt-1",
                },
            },
            {
                "source_event_id": "EVT-2",
                "timeline_bucket": "2026-06-02",
                "published_at": "2026-06-02T10:00:00+08:00",
                "title": "算力公告",
                "source_id": "cninfo",
                "source_type": "announcement",
                "quality_state": "trusted_fact",
                "entities": {
                    "narratives": ["算力"],
                    "tickers": ["000063"],
                    "sectors": ["通信"],
                    "concepts": ["算力"],
                },
                "citations": {
                    "source_id": "cninfo",
                    "source_event_id": "EVT-2",
                    "evidence_id": "EVT-2",
                    "evidence_url": "https://example.com/evt-2",
                },
            },
        ],
    }


def _graph_payload() -> dict[str, object]:
    return {
        "version": "narrative-evidence-graph-v1",
        "narratives": ["AI", "算力"],
        "comparisons": [
            {
                "narratives": ["AI", "算力"],
                "shared_source_event_ids": [],
                "shared_tickers": [],
                "shared_sectors": [],
                "shared_concepts": [],
                "contradictions": [],
                "metrics": {
                    "shared_event_count": 0,
                    "shared_entity_count": 0,
                    "contradiction_count": 0,
                },
            }
        ],
        "edges": [
            {
                "edge_id": "NARRATIVE_AI->supported_by_event->EVENT_EVT-1->EVT-1",
                "from_node_id": "NARRATIVE_AI",
                "to_node_id": "EVENT_EVT-1",
                "edge_type": "supported_by_event",
                "provenance": {"source_event_id": "EVT-1"},
                "confidence": 1.0,
            }
        ],
    }


def _analyst_notes() -> list[dict[str, object]]:
    return [
        {
            "note_id": "NOTE-1",
            "author": "analyst-local",
            "created_at": "2026-06-02T11:00:00+08:00",
            "linked_object_ref": {"object_type": "narrative", "object_id": "AI"},
            "body": "关注 capex 与订单确认节奏。",
            "requested_trust_state": "trusted_fact",
        },
        {
            "note_id": "NOTE-2",
            "author": "analyst-local",
            "created_at": "2026-06-02T11:10:00+08:00",
            "linked_object_ref": {"object_type": "source_event", "object_id": "EVT-2"},
            "body": "需要在晨会前复核公告原文。",
        },
    ]
