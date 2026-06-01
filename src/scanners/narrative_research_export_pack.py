from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_narrative_research_export_pack(
    *,
    timeline_search: dict[str, Any],
    evidence_graph: dict[str, Any],
    analyst_notes: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    events = [_normalize_event(event) for event in _list(timeline_search.get("results"))]
    notes = [_normalize_note(note) for note in analyst_notes or []]
    citations = [_citation_for_event(event) for event in events if event["source_event_id"]]
    narratives = _narratives(events=events, evidence_graph=evidence_graph)
    comparisons = _list(evidence_graph.get("comparisons"))
    return {
        "version": "narrative-research-export-pack-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "narrative_count": len(narratives),
            "source_event_count": len(events),
            "note_count": len(notes),
            "citation_count": len(citations),
            "comparison_count": len(comparisons),
        },
        "contract": {
            "provider_access_allowed": False,
            "notes_promote_trusted_state": False,
            "citation_required_for_export_items": True,
            "auditable_user_artifacts": True,
        },
        "narratives": narratives,
        "source_events": events,
        "comparisons": comparisons,
        "analyst_notes": notes,
        "citations": citations,
        "export_manifest": {
            "format": "json_html",
            "citation_ids": [citation["citation_id"] for citation in citations],
            "linked_object_refs": _linked_object_refs(notes),
            "source_artifacts": [
                "outputs/narrative_research_workbench/current/narrative_timeline_search.json",
                "outputs/narrative_research_workbench/current/narrative_evidence_graph.json",
            ],
            "non_promotional_note_policy": "notes are auditable user artifacts and do not change trusted state",
        },
    }


def render_narrative_research_export_pack_html(pack: dict[str, Any]) -> str:
    summary = _mapping(pack.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>研究导出包与分析师笔记</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>研究导出包与分析师笔记</h1>",
            '<section class="summary">',
            _html_kv("叙事", summary.get("narrative_count", 0)),
            _html_kv("来源事件", summary.get("source_event_count", 0)),
            _html_kv("分析师笔记", summary.get("note_count", 0)),
            _html_kv("引用", summary.get("citation_count", 0)),
            "<p>笔记不会提升可信状态；导出包只引用已有来源事件和证据图谱 artifact。</p>",
            "</section>",
            _notes_section(_list(pack.get("analyst_notes"))),
            _citations_table(_list(pack.get("citations"))),
            _events_table(_list(pack.get("source_events"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _normalize_event(event: Any) -> dict[str, Any]:
    row = _mapping(event)
    entities = _mapping(row.get("entities"))
    citations = _mapping(row.get("citations"))
    source_event_id = str(row.get("source_event_id") or citations.get("source_event_id") or "")
    return {
        "source_event_id": source_event_id,
        "timeline_bucket": str(row.get("timeline_bucket") or str(row.get("published_at") or "")[:10]),
        "published_at": str(row.get("published_at") or ""),
        "title": str(row.get("title") or ""),
        "source_id": str(row.get("source_id") or citations.get("source_id") or ""),
        "source_type": str(row.get("source_type") or ""),
        "quality_state": str(row.get("quality_state") or ""),
        "entities": {
            "narratives": _strings(entities.get("narratives")),
            "tickers": _strings(entities.get("tickers")),
            "sectors": _strings(entities.get("sectors")),
            "concepts": _strings(entities.get("concepts")),
        },
        "citation_id": f"CITE_{source_event_id}",
    }


def _normalize_note(note: Any) -> dict[str, Any]:
    row = _mapping(note)
    linked_ref = _mapping(row.get("linked_object_ref"))
    return {
        "note_id": str(row.get("note_id") or ""),
        "author": str(row.get("author") or "local-analyst"),
        "created_at": str(row.get("created_at") or ""),
        "linked_object_ref": {
            "object_type": str(linked_ref.get("object_type") or ""),
            "object_id": str(linked_ref.get("object_id") or ""),
        },
        "body": str(row.get("body") or ""),
        "promotion_effect": "none",
        "audit": {
            "user_artifact": True,
            "trusted_state_mutation_allowed": False,
        },
    }


def _citation_for_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation_id": event["citation_id"],
        "source_event_id": event["source_event_id"],
        "source_id": event["source_id"],
        "title": event["title"],
        "quality_state": event["quality_state"],
    }


def _narratives(*, events: list[dict[str, Any]], evidence_graph: dict[str, Any]) -> list[str]:
    values = {
        narrative
        for event in events
        for narrative in event["entities"]["narratives"]
    }
    values.update(str(narrative) for narrative in _list(evidence_graph.get("narratives")) if str(narrative))
    return sorted(values)


def _linked_object_refs(notes: list[dict[str, Any]]) -> list[dict[str, str]]:
    refs = []
    seen = set()
    for note in notes:
        ref = _mapping(note.get("linked_object_ref"))
        normalized = {
            "object_id": str(ref.get("object_id") or ""),
            "object_type": str(ref.get("object_type") or ""),
        }
        key = (normalized["object_type"], normalized["object_id"])
        if key == ("", "") or key in seen:
            continue
        seen.add(key)
        refs.append(normalized)
    return refs


def _notes_section(notes: list[Any]) -> str:
    rows = [_mapping(note) for note in notes]
    if not rows:
        return "<section><h2>分析师笔记</h2><p>当前导出包没有本地分析师笔记。</p></section>"
    items = "".join(
        "<article class=\"note\">"
        f"<h3>{_html_text(row.get('note_id'))}</h3>"
        f"<p>{_html_text(row.get('body'))}</p>"
        f"<p>关联对象: {_html_text(_mapping(row.get('linked_object_ref')).get('object_type'))}"
        f"/{_html_text(_mapping(row.get('linked_object_ref')).get('object_id'))}</p>"
        f"<p>Promotion: {_html_text(row.get('promotion_effect'))}</p>"
        "</article>"
        for row in rows
    )
    return f"<section><h2>分析师笔记</h2>{items}</section>"


def _citations_table(citations: list[Any]) -> str:
    rows = [_mapping(citation) for citation in citations]
    if not rows:
        return "<section><h2>引用清单</h2><p>没有可导出的引用。</p></section>"
    header = "".join(_th(label) for label in ("引用 ID", "来源事件", "来源", "标题", "质量"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('citation_id'))}</td>"
        f"<td>{_html_text(row.get('source_event_id'))}</td>"
        f"<td>{_html_text(row.get('source_id'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(row.get('quality_state'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>引用清单</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _events_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>来源事件</h2><p>没有来源事件。</p></section>"
    header = "".join(_th(label) for label in ("日期", "标题", "叙事", "股票", "质量"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('timeline_bucket'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(', '.join(_strings(_mapping(row.get('entities')).get('narratives'))))}</td>"
        f"<td>{_html_text(', '.join(_strings(_mapping(row.get('entities')).get('tickers'))))}</td>"
        f"<td>{_html_text(row.get('quality_state'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>来源事件</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _th(label: str) -> str:
    return f"<th>{_html_text(label)}</th>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
h3 { font-size: 16px; margin: 0 0 8px; }
.summary, .note { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
.note { margin: 10px 0; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; }
th { background: #eef2f7; font-size: 13px; }
td { font-size: 13px; }
""".strip()
