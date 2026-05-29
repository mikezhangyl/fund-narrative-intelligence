from __future__ import annotations

import hashlib
from html import escape
from typing import Any

from src.scanners.mapping_evidence_pack_report import (
    build_mapping_evidence_pack_report,
    render_html_report,
)
from src.scanners.source_event_schema import validate_source_event


def build_announcement_mapping_intake_report(
    *,
    event_payload: dict[str, Any],
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    packs = announcement_events_to_evidence_packs(
        event_payload=event_payload,
        registry_payload=registry_payload,
    )
    evidence_payload = {
        "version": "announcement-mapping-evidence-pack-v1",
        "trust_status": "candidate_untrusted",
        "methodology": "announcement source events become review-only mapping evidence candidates.",
        "packs": packs,
    }
    report = build_mapping_evidence_pack_report(evidence_payload=evidence_payload)
    detail_view = _evidence_detail_view(packs)
    return {
        **report,
        "version": "announcement-mapping-intake-v1",
        "summary": {
            **report["summary"],
            "announcement_event_count": len({item["event_id"] for item in detail_view}),
            "quality_gap_count": sum(len(item["quality_gaps"]) for item in detail_view),
        },
        "source_event_schema": {
            "version": "source-event-schema-v1",
            "source_type": "announcement",
        },
        "evidence_detail_view": detail_view,
    }


def announcement_events_to_evidence_packs(
    *,
    event_payload: dict[str, Any],
    registry_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    registry_index = _registry_index(registry_payload)
    grouped: dict[str, dict[str, Any]] = {}
    for event in _announcement_events(event_payload):
        for stock in _list(event.get("mentioned_stocks")):
            stock_code = str(stock.get("stock_code") or "")
            if not stock_code:
                continue
            pack = grouped.setdefault(
                stock_code,
                {
                    "stock_code": stock_code,
                    "stock_name": str(stock.get("stock_name") or ""),
                    "proposed_mappings": [],
                },
            )
            pack["proposed_mappings"].extend(
                _mappings_for_event(event, stock_code=stock_code, registry_index=registry_index)
            )
    return [grouped[key] for key in sorted(grouped)]


def render_announcement_mapping_intake_html(report: dict[str, Any]) -> str:
    base = render_html_report(report)
    return base.replace("</main>", f"{_detail_section(report.get('evidence_detail_view'))}\n</main>")


def _announcement_events(event_payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for event in _list(event_payload.get("events")):
        normalized = validate_source_event(event)
        if normalized["source_type"] == "announcement":
            events.append(normalized)
    return events


def _mappings_for_event(
    event: dict[str, Any],
    *,
    stock_code: str,
    registry_index: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    mappings = []
    for candidate in _list(event.get("candidate_narratives")):
        target = _target_narrative(candidate, registry_index)
        confidence = _float(candidate.get("confidence"))
        mappings.append(
            {
                "candidate_mapping_id": _stable_id(
                    "AMAP",
                    [stock_code, target["id"], event["event_id"]],
                ),
                "narrative_id": target["id"],
                "narrative_name": target["name"],
                "target_is_existing_narrative": target["is_existing"],
                "trust_status": "candidate_untrusted",
                "mapping_rationale": (
                    f"Announcement evidence from {event['provider']} links {stock_code} "
                    f"to {target['name']} for human review."
                ),
                "exclusion_rationale": [
                    "Announcement evidence alone cannot promote a trusted mapping.",
                    "PDF parsing quality is outside this slice unless structured summary is provided.",
                ],
                "confidence_components": {
                    "announcement_relevance": confidence,
                    "evidence_quality": 0.5 if event.get("quality_gaps") else 0.8,
                },
                "evidence_items": [_evidence_item(event)],
            }
        )
    return mappings


def _evidence_item(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_event_id": str(event.get("event_id") or ""),
        "source_name": str(event.get("provider") or ""),
        "source_url": str(event.get("source_url") or ""),
        "source_type": "announcement",
        "evidence_date": _event_date(event),
        "title": str(event.get("title") or ""),
        "evidence_summary": str(event.get("summary") or ""),
        "supports": _strings(event.get("evidence_claims")),
        "supported_claim_types": _strings(event.get("evidence_claims")),
        "quality_gaps": _strings(event.get("quality_gaps")),
        "trust_status": "candidate_untrusted",
    }


def _event_date(event: dict[str, Any]) -> str:
    event_time = str(event.get("event_time") or "")
    return event_time[:10] if event_time else ""


def _evidence_detail_view(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for pack in packs:
        for mapping in _list(pack.get("proposed_mappings")):
            for evidence in _list(mapping.get("evidence_items")):
                rows.append(
                    {
                        "event_id": str(evidence.get("source_event_id") or ""),
                        "stock_code": str(pack.get("stock_code") or ""),
                        "stock_name": str(pack.get("stock_name") or ""),
                        "narrative_id": str(mapping.get("narrative_id") or ""),
                        "narrative_name": str(mapping.get("narrative_name") or ""),
                        "title": str(evidence.get("title") or ""),
                        "source_url": str(evidence.get("source_url") or ""),
                        "evidence_date": str(evidence.get("evidence_date") or ""),
                        "supported_claim_types": _strings(evidence.get("supported_claim_types")),
                        "quality_gaps": _strings(evidence.get("quality_gaps")),
                        "trust_status": str(evidence.get("trust_status") or "candidate_untrusted"),
                    }
                )
    return rows


def _registry_index(registry_payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for narrative in _list(registry_payload.get("narratives")):
        narrative_id = str(narrative.get("narrative_id") or "")
        name = str(narrative.get("display_name") or narrative.get("name") or narrative_id)
        payload = {"narrative_id": narrative_id, "narrative_name": name}
        if narrative_id:
            index[narrative_id] = payload
        for term in {
            str(narrative.get("display_name") or ""),
            str(narrative.get("name") or ""),
            *_strings(narrative.get("aliases")),
            *_strings(narrative.get("related_terms")),
        }:
            if term:
                index[_normalize_name(term)] = payload
    return index


def _target_narrative(
    candidate: dict[str, Any],
    registry_index: dict[str, dict[str, str]],
) -> dict[str, Any]:
    narrative_id = str(candidate.get("narrative_id") or "")
    existing = registry_index.get(narrative_id) if narrative_id else None
    if not existing:
        existing = registry_index.get(_normalize_name(str(candidate.get("name") or "")))
    if existing:
        return {
            "id": existing["narrative_id"],
            "name": existing["narrative_name"],
            "is_existing": True,
        }
    name = str(candidate.get("name") or "")
    return {
        "id": narrative_id or _stable_id("C_INTAKE", [name]),
        "name": name,
        "is_existing": False,
    }


def _detail_section(value: Any) -> str:
    rows = value if isinstance(value, list) else []
    if not rows:
        return '<section><h2>公告证据详情</h2><p class="empty">没有返回可展示数据。</p></section>'
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('stock_code'))}</td>"
        f"<td>{_html_text(row.get('narrative_name'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(_cell(row.get('supported_claim_types')))}</td>"
        f"<td>{_html_text(_cell(row.get('quality_gaps')))}</td>"
        f"<td>{_html_text(row.get('trust_status'))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        "<section><h2>公告证据详情</h2>"
        "<table><thead><tr><th>股票</th><th>叙事</th><th>公告标题</th>"
        "<th>支持口径</th><th>质量缺口</th><th>状态</th></tr></thead>"
        f"<tbody>{body}</tbody></table></section>"
    )


def _normalize_name(value: str) -> str:
    return "".join(value.lower().split())


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1("|".join(str(value or "") for value in values).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:12].upper()}"


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return round(float(value), 6)


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _cell(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)
