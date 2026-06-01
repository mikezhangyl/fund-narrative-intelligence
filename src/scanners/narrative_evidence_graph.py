from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_narrative_evidence_graph(
    *,
    source_events: list[dict[str, Any]],
    narratives: list[str],
    generated_at: str | None = None,
) -> dict[str, Any]:
    narrative_names = [name for name in _unique(narratives) if name]
    events = [_normalize_event(event) for event in source_events]
    matched_events = [
        event
        for event in events
        if any(narrative in event["entities"]["narratives"] for narrative in narrative_names)
    ]
    nodes, edges = _build_graph(narrative_names=narrative_names, events=matched_events)
    comparisons = [_comparison(narrative_names=narrative_names, events=matched_events)] if len(narrative_names) >= 2 else []
    return {
        "version": "narrative-evidence-graph-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "narrative_count": len(narrative_names),
            "event_count": len(matched_events),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "unsupported_inference_count": 0,
        },
        "contract": {
            "provider_access_allowed": False,
            "unsupported_inferred_links_allowed": False,
            "edge_provenance_required": True,
            "confidence_policy": "explicit_event_or_entity_only",
        },
        "narratives": narrative_names,
        "nodes": nodes,
        "edges": edges,
        "comparisons": comparisons,
    }


def render_narrative_evidence_graph_html(graph: dict[str, Any]) -> str:
    summary = _mapping(graph.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>叙事比较与证据图谱</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>叙事比较与证据图谱</h1>",
            '<section class="summary">',
            _html_kv("节点", summary.get("node_count", 0)),
            _html_kv("边", summary.get("edge_count", 0)),
            _html_kv("Unsupported inference", summary.get("unsupported_inference_count", 0)),
            "<p>图谱只展示显式来源事件和实体关系，不创建无证据推断边。</p>",
            "</section>",
            _comparison_section(_list(graph.get("comparisons"))),
            _edges_table(_list(graph.get("edges"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _build_graph(*, narrative_names: list[str], events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    for narrative in narrative_names:
        _add_node(nodes, _node("narrative", f"NARRATIVE_{narrative}", narrative))
    for event in events:
        event_node = _node("source_event", f"EVENT_{event['source_event_id']}", event["title"])
        event_node["source_event_id"] = event["source_event_id"]
        event_node["quality_state"] = event["quality_state"]
        _add_node(nodes, event_node)
        for narrative in narrative_names:
            if narrative in event["entities"]["narratives"]:
                _add_edge(
                    edges,
                    from_node_id=f"NARRATIVE_{narrative}",
                    to_node_id=event_node["node_id"],
                    edge_type="supported_by_event",
                    source_event_id=event["source_event_id"],
                    confidence=1.0 if event["degradation_status"] in {"", "ok"} else 0.4,
                )
        for ticker in event["entities"]["tickers"]:
            _add_entity_node_and_edge(nodes, edges, event, "stock", f"STOCK_{ticker}", ticker, "mentions_stock")
        for sector in event["entities"]["sectors"]:
            _add_entity_node_and_edge(nodes, edges, event, "sector", f"SECTOR_{sector}", sector, "mentions_sector")
        for concept in event["entities"]["concepts"]:
            _add_entity_node_and_edge(nodes, edges, event, "concept", f"CONCEPT_{concept}", concept, "mentions_concept")
    return list(nodes.values()), list(edges.values())


def _comparison(*, narrative_names: list[str], events: list[dict[str, Any]]) -> dict[str, Any]:
    narrative_sets = {
        narrative: [
            event
            for event in events
            if narrative in event["entities"]["narratives"]
        ]
        for narrative in narrative_names
    }
    shared_events = sorted(
        {
            event["source_event_id"]
            for event in events
            if all(narrative in event["entities"]["narratives"] for narrative in narrative_names)
        }
    )
    shared_tickers = _shared_entity_values(narrative_sets, "tickers")
    shared_sectors = _shared_entity_values(narrative_sets, "sectors")
    shared_concepts = _shared_entity_values(narrative_sets, "concepts")
    contradictions = [
        {
            "source_event_id": event["source_event_id"],
            "reason": "degraded source event cannot support trusted comparison",
        }
        for event in events
        if event["source_event_id"] in shared_events and event["degradation_status"] not in {"", "ok"}
    ]
    return {
        "narratives": narrative_names,
        "shared_source_event_ids": shared_events,
        "shared_tickers": shared_tickers,
        "shared_sectors": shared_sectors,
        "shared_concepts": shared_concepts,
        "contradictions": contradictions,
        "metrics": {
            "shared_event_count": len(shared_events),
            "shared_entity_count": len(shared_tickers) + len(shared_sectors) + len(shared_concepts),
            "contradiction_count": len(contradictions),
        },
    }


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    entities = _mapping(event.get("entities"))
    source_event_id = str(
        event.get("source_event_id")
        or _mapping(event.get("citations")).get("source_event_id")
        or event.get("id")
        or ""
    )
    return {
        "source_event_id": source_event_id,
        "title": str(event.get("title") or ""),
        "source_id": str(event.get("source_id") or event.get("provider") or ""),
        "quality_state": str(event.get("quality_state") or ""),
        "degradation_status": str(event.get("degradation_status") or ""),
        "entities": {
            "narratives": _strings(entities.get("narratives") or event.get("narrative_hints")),
            "tickers": _strings(entities.get("tickers") or event.get("stock_codes")),
            "sectors": _strings(entities.get("sectors") or event.get("sectors")),
            "concepts": _strings(entities.get("concepts") or event.get("concepts")),
        },
        "citations": _mapping(event.get("citations")),
    }


def _add_entity_node_and_edge(
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
    event: dict[str, Any],
    node_type: str,
    node_id: str,
    label: str,
    edge_type: str,
) -> None:
    _add_node(nodes, _node(node_type, node_id, label))
    _add_edge(
        edges,
        from_node_id=f"EVENT_{event['source_event_id']}",
        to_node_id=node_id,
        edge_type=edge_type,
        source_event_id=event["source_event_id"],
        confidence=1.0,
    )


def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    nodes.setdefault(node["node_id"], node)


def _add_edge(
    edges: dict[str, dict[str, Any]],
    *,
    from_node_id: str,
    to_node_id: str,
    edge_type: str,
    source_event_id: str,
    confidence: float,
) -> None:
    edge_id = f"{from_node_id}->{edge_type}->{to_node_id}->{source_event_id}"
    edges.setdefault(
        edge_id,
        {
            "edge_id": edge_id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "edge_type": edge_type,
            "provenance": {"source_event_id": source_event_id},
            "confidence": confidence,
        },
    )


def _node(node_type: str, node_id: str, label: str) -> dict[str, Any]:
    return {"node_id": node_id, "node_type": node_type, "label": label}


def _shared_entity_values(narrative_sets: dict[str, list[dict[str, Any]]], field: str) -> list[str]:
    value_sets = []
    for events in narrative_sets.values():
        values = {
            value
            for event in events
            for value in event["entities"][field]
        }
        value_sets.append(values)
    if not value_sets:
        return []
    return sorted(set.intersection(*value_sets))


def _comparison_section(comparisons: list[Any]) -> str:
    if not comparisons:
        return "<section><h2>比较</h2><p>至少选择两个叙事后生成比较。</p></section>"
    rows = []
    for comparison in comparisons:
        row = _mapping(comparison)
        rows.append(
            "<tr>"
            f"<td>{_html_text(', '.join(_strings(row.get('narratives'))))}</td>"
            f"<td>{_html_text(', '.join(_strings(row.get('shared_source_event_ids'))))}</td>"
            f"<td>{_html_text(', '.join(_strings(row.get('shared_tickers'))))}</td>"
            f"<td>{_html_text(len(_list(row.get('contradictions'))))}</td>"
            "</tr>"
        )
    return (
        "<section><h2>共享事件</h2><table><thead><tr>"
        "<th>叙事</th><th>共享事件</th><th>共享股票</th><th>矛盾/降级</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></section>"
    )


def _edges_table(edges: list[Any]) -> str:
    rows = [_mapping(edge) for edge in edges]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("From", "Type", "To", "Evidence")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(edge.get('from_node_id'))}</td>"
        f"<td>{_html_text(edge.get('edge_type'))}</td>"
        f"<td>{_html_text(edge.get('to_node_id'))}</td>"
        f"<td>{_html_text(_mapping(edge.get('provenance')).get('source_event_id'))}</td>"
        "</tr>"
        for edge in rows
    )
    return f"<section><h2>图谱边</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _unique(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
