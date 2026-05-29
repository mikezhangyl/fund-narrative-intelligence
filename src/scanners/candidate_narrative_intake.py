from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.source_event_schema import SCHEMA_VERSION, validate_source_event

SOURCE_TYPES = {"news", "announcement", "social", "social_future", "manual"}


def build_candidate_narrative_intake_report(
    *,
    event_payload: dict[str, Any],
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    events = [_event_payload(event) for event in _list(event_payload.get("events"))]
    registry_index = _registry_index(registry_payload)
    new_candidates = _new_candidate_narratives(events, registry_index)
    existing_evidence = _existing_narrative_evidence(events, registry_index)
    mapping_candidates = _candidate_stock_mappings(events, registry_index)
    review_queue = _intake_review_queue(new_candidates, mapping_candidates)
    return {
        "version": "candidate-narrative-intake-v1",
        "generated_at": _utc_now(),
        "status": "candidate_untrusted",
        "source_event_schema": {
            "version": SCHEMA_VERSION,
            "config": "config/source_event_schema.json",
        },
        "summary": {
            "event_count": len(events),
            "source_type_count": len({event["source_type"] for event in events}),
            "new_candidate_narrative_count": len(new_candidates),
            "existing_narrative_evidence_count": len(existing_evidence),
            "candidate_mapping_count": len(mapping_candidates),
            "review_queue_item_count": review_queue["summary"]["total_count"],
        },
        "source_type_counts": dict(sorted(Counter(event["source_type"] for event in events).items())),
        "events": events,
        "new_candidate_narratives": new_candidates,
        "existing_narrative_evidence": existing_evidence,
        "candidate_stock_mappings": mapping_candidates,
        "intake_review_queue": review_queue,
        "promotion_policy": {
            "automatic_registry_write": False,
            "automatic_mapping_write": False,
            "default_trust_status": "candidate_untrusted",
            "required_next_step": "human_review",
        },
        "disclaimer": (
            "Candidate narrative intake is a staging layer. It must not mutate "
            "reviewed or trusted narrative stores automatically."
        ),
    }


def render_html_report(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>候选叙事接入口报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>候选叙事接入口报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", report.get("status", "")),
            _html_kv("生成时间", report.get("generated_at", "")),
            "<p>本报告只生成 candidate_untrusted 候选项，不写入 reviewed registry 或 trusted mapping store。</p>",
            "</section>",
            "<section>",
            "<h2>接入概览</h2>",
            '<div class="metrics">',
            _html_metric("事件数", summary.get("event_count", 0)),
            _html_metric("来源类型", summary.get("source_type_count", 0)),
            _html_metric("新候选叙事", summary.get("new_candidate_narrative_count", 0)),
            _html_metric("已有叙事证据", summary.get("existing_narrative_evidence_count", 0)),
            _html_metric("候选股票映射", summary.get("candidate_mapping_count", 0)),
            "</div>",
            "</section>",
            _rows_section(
                "新候选叙事",
                report.get("new_candidate_narratives"),
                (
                    ("candidate_narrative_id", "候选ID"),
                    ("name", "名称"),
                    ("canonical_taxonomy", "分类"),
                    ("triggering_stock_codes", "触发股票"),
                    ("source_event_count", "事件数"),
                    ("trust_status", "状态"),
                ),
            ),
            _rows_section(
                "已有叙事证据补强",
                report.get("existing_narrative_evidence"),
                (
                    ("narrative_id", "叙事ID"),
                    ("narrative_name", "叙事"),
                    ("event_count", "事件数"),
                    ("mentioned_stock_codes", "股票"),
                    ("source_types", "来源"),
                ),
            ),
            _rows_section(
                "候选股票映射",
                report.get("candidate_stock_mappings"),
                (
                    ("stock_code", "股票"),
                    ("stock_name", "名称"),
                    ("target_narrative_name", "候选叙事"),
                    ("source_event_id", "来源事件"),
                    ("confidence", "置信度"),
                    ("trust_status", "状态"),
                ),
            ),
            _rows_section(
                "Review Queue",
                _mapping(report.get("intake_review_queue")).get("items"),
                (
                    ("review_item_id", "审查项"),
                    ("item_type", "类型"),
                    ("title", "标题"),
                    ("default_action", "默认动作"),
                ),
            ),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_source_event(event)
    source_type = str(normalized.get("source_type") or "manual")
    if source_type not in SOURCE_TYPES:
        source_type = "manual"
    return {
        "schema_version": str(normalized.get("schema_version") or ""),
        "event_id": str(normalized.get("event_id") or _stable_id("EVT", [event])),
        "dedupe_key": str(normalized.get("dedupe_key") or ""),
        "source_type": source_type,
        "event_time": str(normalized.get("event_time") or ""),
        "title": str(normalized.get("title") or ""),
        "summary": str(normalized.get("summary") or ""),
        "source_name": str(normalized.get("provider") or event.get("source_name") or ""),
        "source_url": str(normalized.get("source_url") or ""),
        "source_metadata": _mapping(normalized.get("source_metadata")),
        "quality_gaps": _strings(normalized.get("quality_gaps")),
        "evidence_claims": _strings(normalized.get("evidence_claims")),
        "trust_status": str(normalized.get("trust_status") or "candidate_untrusted"),
        "promotion_effect": str(normalized.get("promotion_effect") or "none"),
        "mentioned_stocks": [_stock_payload(item) for item in _list(normalized.get("mentioned_stocks"))],
        "stock_codes": _strings(normalized.get("stock_codes")),
        "keywords": _strings(normalized.get("keywords")),
        "candidate_narratives": [
            _event_candidate_payload(item)
            for item in _list(normalized.get("candidate_narratives"))
        ],
    }


def _stock_payload(stock: dict[str, Any]) -> dict[str, str]:
    return {
        "stock_code": str(stock.get("stock_code") or ""),
        "stock_name": str(stock.get("stock_name") or ""),
    }


def _event_candidate_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "narrative_id": str(candidate.get("narrative_id") or ""),
        "name": str(candidate.get("name") or candidate.get("display_name") or ""),
        "canonical_taxonomy": str(candidate.get("canonical_taxonomy") or ""),
        "confidence": _rounded(_float(candidate.get("confidence"))),
    }


def _registry_index(registry_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for narrative in _list(registry_payload.get("narratives")):
        narrative_id = str(narrative.get("narrative_id") or "")
        names = {
            str(narrative.get("display_name") or ""),
            str(narrative.get("name") or ""),
            *_strings(narrative.get("aliases")),
            *_strings(narrative.get("related_terms")),
        }
        payload = {
            "narrative_id": narrative_id,
            "narrative_name": str(narrative.get("display_name") or narrative.get("name") or narrative_id),
        }
        if narrative_id:
            index[narrative_id] = payload
        for name in names:
            if name:
                index[_normalize_name(name)] = payload
    return index


def _new_candidate_narratives(
    events: list[dict[str, Any]],
    registry_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        for candidate in _list(event.get("candidate_narratives")):
            if _existing_narrative(candidate, registry_index):
                continue
            name = str(candidate.get("name") or "")
            if not name:
                continue
            key = _normalize_name(name)
            current = grouped.setdefault(
                key,
                {
                    "candidate_narrative_id": _stable_id("C_INTAKE", [name]),
                    "name": name,
                    "canonical_taxonomy": str(candidate.get("canonical_taxonomy") or ""),
                    "status": "candidate",
                    "trust_status": "candidate_untrusted",
                    "human_review_status": "candidate",
                    "source": "candidate_narrative_intake",
                    "triggering_stock_codes": set(),
                    "keywords": set(),
                    "source_event_ids": [],
                    "source_types": set(),
                    "confidence_values": [],
                },
            )
            current["source_event_ids"].append(event["event_id"])
            current["source_types"].add(event["source_type"])
            current["keywords"].update(event["keywords"])
            current["confidence_values"].append(_float(candidate.get("confidence")))
            current["triggering_stock_codes"].update(
                stock["stock_code"] for stock in event["mentioned_stocks"] if stock["stock_code"]
            )
    rows = []
    for item in grouped.values():
        rows.append(
            {
                "candidate_narrative_id": item["candidate_narrative_id"],
                "name": item["name"],
                "canonical_taxonomy": item["canonical_taxonomy"],
                "status": item["status"],
                "trust_status": item["trust_status"],
                "human_review_status": item["human_review_status"],
                "source": item["source"],
                "triggering_stock_codes": sorted(item["triggering_stock_codes"]),
                "keywords": sorted(item["keywords"]),
                "source_event_ids": item["source_event_ids"],
                "source_event_count": len(item["source_event_ids"]),
                "source_types": sorted(item["source_types"]),
                "confidence": _rounded(sum(item["confidence_values"]) / len(item["confidence_values"])),
                "rationale": (
                    f"Candidate generated from {len(item['source_event_ids'])} intake "
                    f"event(s): {', '.join(sorted(item['keywords'])[:5])}."
                ),
            }
        )
    return sorted(rows, key=lambda row: (-row["source_event_count"], row["name"]))


def _existing_narrative_evidence(
    events: list[dict[str, Any]],
    registry_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        for candidate in _list(event.get("candidate_narratives")):
            existing = _existing_narrative(candidate, registry_index)
            if not existing:
                continue
            narrative_id = existing["narrative_id"]
            current = grouped.setdefault(
                narrative_id,
                {
                    "narrative_id": narrative_id,
                    "narrative_name": existing["narrative_name"],
                    "source_event_ids": [],
                    "source_types": set(),
                    "mentioned_stock_codes": set(),
                    "keywords": set(),
                },
            )
            current["source_event_ids"].append(event["event_id"])
            current["source_types"].add(event["source_type"])
            current["keywords"].update(event["keywords"])
            current["mentioned_stock_codes"].update(
                stock["stock_code"] for stock in event["mentioned_stocks"] if stock["stock_code"]
            )
    return [
        {
            "narrative_id": item["narrative_id"],
            "narrative_name": item["narrative_name"],
            "event_count": len(item["source_event_ids"]),
            "source_event_ids": item["source_event_ids"],
            "source_types": sorted(item["source_types"]),
            "mentioned_stock_codes": sorted(item["mentioned_stock_codes"]),
            "keywords": sorted(item["keywords"]),
            "trust_status": "candidate_untrusted",
        }
        for item in sorted(grouped.values(), key=lambda row: row["narrative_name"])
    ]


def _candidate_stock_mappings(
    events: list[dict[str, Any]],
    registry_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for event in events:
        for candidate in _list(event.get("candidate_narratives")):
            target = _target_narrative(candidate, registry_index)
            for stock in event["mentioned_stocks"]:
                stock_code = stock["stock_code"]
                key = (stock_code, target["id"], event["event_id"])
                if not stock_code or key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "candidate_mapping_id": _stable_id("CMAP", [stock_code, target["id"], event["event_id"]]),
                        "stock_code": stock_code,
                        "stock_name": stock["stock_name"],
                        "target_narrative_id": target["id"],
                        "target_narrative_name": target["name"],
                        "target_is_existing_narrative": target["is_existing"],
                        "source_event_id": event["event_id"],
                        "source_type": event["source_type"],
                        "source_url": event["source_url"],
                        "keywords": event["keywords"],
                        "confidence": _rounded(_float(candidate.get("confidence"))),
                        "trust_status": "candidate_untrusted",
                        "default_action": "defer",
                    }
                )
    return sorted(rows, key=lambda row: (row["stock_code"], row["target_narrative_name"], row["source_event_id"]))


def _intake_review_queue(
    new_candidates: list[dict[str, Any]],
    mapping_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    items = []
    for candidate in new_candidates:
        items.append(
            {
                "review_item_id": f"IRQ_{candidate['candidate_narrative_id']}",
                "item_type": "candidate_narrative",
                "title": candidate["name"],
                "trust_status": "candidate_untrusted",
                "default_action": "defer",
                "available_actions": ["approve_for_reviewed", "reject", "defer"],
                "payload_ref": candidate["candidate_narrative_id"],
            }
        )
    for mapping in mapping_candidates:
        items.append(
            {
                "review_item_id": f"IRQ_{mapping['candidate_mapping_id']}",
                "item_type": "candidate_mapping",
                "title": f"{mapping['stock_code']} -> {mapping['target_narrative_name']}",
                "trust_status": "candidate_untrusted",
                "default_action": "defer",
                "available_actions": ["approve_for_evidence_pack", "reject", "defer"],
                "payload_ref": mapping["candidate_mapping_id"],
            }
        )
    return {
        "version": "candidate-narrative-intake-review-queue-v1",
        "summary": {
            "total_count": len(items),
            "candidate_narrative_count": len(new_candidates),
            "candidate_mapping_count": len(mapping_candidates),
            "action_required": bool(items),
        },
        "items": items,
    }


def _target_narrative(candidate: dict[str, Any], registry_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    existing = _existing_narrative(candidate, registry_index)
    if existing:
        return {
            "id": existing["narrative_id"],
            "name": existing["narrative_name"],
            "is_existing": True,
        }
    name = str(candidate.get("name") or "")
    return {
        "id": _stable_id("C_INTAKE", [name]),
        "name": name,
        "is_existing": False,
    }


def _existing_narrative(
    candidate: dict[str, Any],
    registry_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    narrative_id = str(candidate.get("narrative_id") or "")
    if narrative_id and narrative_id in registry_index:
        return registry_index[narrative_id]
    name = str(candidate.get("name") or "")
    if name:
        return registry_index.get(_normalize_name(name))
    return None


def _rows_section(
    title: str,
    value: Any,
    columns: tuple[tuple[str, str], ...],
) -> str:
    rows = _list(value)
    return "\n".join(
        [
            "<section>",
            f"<h2>{_html_text(title)}</h2>",
            _rows_table(rows, columns),
            "</section>",
        ]
    )


def _rows_table(rows: list[dict[str, Any]], columns: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return '<p class="empty">没有返回可展示数据。</p>'
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{_html_text(_cell_value(row.get(field)))}</td>"
            for field, _ in columns
        )
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _normalize_name(value: str) -> str:
    return "".join(str(value).lower().split())


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1("|".join(str(value) for value in values).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:12].upper()}"


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _cell_value(value: Any) -> Any:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    return value


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #f59e0b; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #e6ebf1; padding: 8px; text-align: left; vertical-align: top; }
th { color: #475569; background: #f8fafc; }
.empty { color: #8a94a6; }
""".strip()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
