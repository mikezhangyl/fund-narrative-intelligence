from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.trust_state_disclosure import trust_state_display_zh


def build_mapping_evidence_pack_report(
    *,
    evidence_payload: dict[str, Any],
    symbols: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    requested = _requested_symbols(symbols)
    packs = _selected_packs(_list(evidence_payload.get("packs")), requested)
    missing = sorted(set(requested) - {pack["stock_code"] for pack in packs}) if requested else []
    candidate_count = sum(len(_candidate_mappings(pack)) for pack in packs)
    trusted_count = sum(
        1
        for pack in packs
        for mapping in _candidate_mappings(pack)
        if mapping.get("trust_status") == "trusted_validated"
    )
    return {
        "version": "mapping-evidence-pack-report-v1",
        "generated_at": _utc_now(),
        "status": str(evidence_payload.get("trust_status") or "candidate_untrusted"),
        "summary": {
            "requested_symbol_count": len(requested) if requested else len(packs),
            "returned_pack_count": len(packs),
            "candidate_mapping_count": candidate_count,
            "trusted_mapping_count": trusted_count,
            "missing_symbol_count": len(missing),
        },
        "methodology": evidence_payload.get("methodology", ""),
        "packs": [_pack_payload(pack) for pack in packs],
        "missing_symbols": missing,
        "promotion_decision": {
            "can_write_to_reviewed_mapping_store": False,
            "required_next_step": "human_review",
        },
        "disclaimer": (
            "Mapping evidence packs are candidate review inputs only; they are not "
            "trusted mappings, investment advice, trading signals, or predictions."
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
            "<title>股票叙事映射证据包</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>股票叙事映射证据包</h1>",
            '<section class="summary">',
            _html_kv("报告状态", trust_state_display_zh(report.get("status", ""))),
            _html_kv("生成时间", report.get("generated_at", "")),
            (
                "<p>本报告用于人工审核候选股票叙事映射。当前证据包仍为 "
                f"{_html_text(trust_state_display_zh('candidate_untrusted'))}"
                "，不能直接写入可信映射库。</p>"
            ),
            "</section>",
            "<section>",
            "<h2>覆盖概览</h2>",
            '<div class="metrics">',
            _html_metric("请求股票", summary.get("requested_symbol_count", 0)),
            _html_metric("返回证据包", summary.get("returned_pack_count", 0)),
            _html_metric("候选映射", summary.get("candidate_mapping_count", 0)),
            _html_metric("可信映射", summary.get("trusted_mapping_count", 0)),
            _html_metric("缺失股票", summary.get("missing_symbol_count", 0)),
            "</div>",
            "</section>",
            _packs_html(report.get("packs")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _pack_payload(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stock_code": str(pack.get("stock_code") or ""),
        "stock_name": str(pack.get("stock_name") or ""),
        "proposed_mappings": [
            _mapping_payload(mapping)
            for mapping in _list(pack.get("proposed_mappings"))
        ],
    }


def _mapping_payload(mapping: dict[str, Any]) -> dict[str, Any]:
    evidence = _list(mapping.get("evidence_items"))
    return {
        "narrative_id": str(mapping.get("narrative_id") or ""),
        "narrative_name": str(mapping.get("narrative_name") or ""),
        "trust_status": str(mapping.get("trust_status") or "candidate_untrusted"),
        "mapping_rationale": str(mapping.get("mapping_rationale") or ""),
        "exclusion_rationale": _strings(mapping.get("exclusion_rationale")),
        "confidence_components": _mapping(mapping.get("confidence_components")),
        "evidence_source_count": len(evidence),
        "evidence_items": evidence,
    }


def _selected_packs(
    packs: list[dict[str, Any]],
    requested: list[str],
) -> list[dict[str, Any]]:
    if not requested:
        return packs
    requested_set = set(requested)
    return [pack for pack in packs if str(pack.get("stock_code") or "") in requested_set]


def _candidate_mappings(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return _list(pack.get("proposed_mappings"))


def _requested_symbols(symbols: tuple[str, ...] | None) -> list[str]:
    if not symbols:
        return []
    seen = set()
    ordered = []
    for symbol in symbols:
        normalized = str(symbol).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _packs_html(value: Any) -> str:
    packs = _list(value)
    if not packs:
        return '<section><h2>证据包</h2><p class="empty">没有返回可展示数据。</p></section>'
    sections = ["<section><h2>证据包</h2>"]
    for pack in packs:
        sections.append(f"<h3>{_html_text(pack.get('stock_code'))} {_html_text(pack.get('stock_name'))}</h3>")
        for mapping in _list(pack.get("proposed_mappings")):
            sections.append(
                "<div class=\"mapping\">"
                f"<h4>{_html_text(mapping.get('narrative_name'))} "
                "<span>"
                f"{_html_text(trust_state_display_zh(mapping.get('trust_status')))}"
                "</span></h4>"
                f"<p><strong>映射理由:</strong> {_html_text(mapping.get('mapping_rationale'))}</p>"
                f"<p><strong>排除理由:</strong> {_html_text(_cell_value(mapping.get('exclusion_rationale')))}</p>"
                f"<p><strong>证据:</strong> {_html_text(_evidence_summary(mapping.get('evidence_items')))}</p>"
                "</div>"
            )
    sections.append("</section>")
    return "\n".join(sections)


def _evidence_summary(value: Any) -> str:
    return "; ".join(
        f"{item.get('source_name', '')} ({item.get('source_type', '')})"
        for item in _list(value)
    )


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


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
h3 { font-size: 17px; margin: 16px 0 8px; }
h4 { font-size: 15px; margin: 0 0 8px; }
h4 span { color: #92400e; font-size: 12px; margin-left: 6px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #f59e0b; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
.mapping { border: 1px solid #e5e7eb; padding: 12px; margin: 10px 0; background: #fcfcfd; }
.empty { color: #8a94a6; }
""".strip()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
