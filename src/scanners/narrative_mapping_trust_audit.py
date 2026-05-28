from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def execute_narrative_mapping_trust_audit(
    *,
    registry_payload: dict[str, Any],
    mapping_payload: dict[str, Any],
) -> dict[str, Any]:
    registry_audit = _registry_audit(registry_payload)
    mapping_audit = _mapping_audit(mapping_payload, registry_audit["narrative_ids"])
    blockers = _blockers(registry_audit=registry_audit, mapping_audit=mapping_audit)
    warnings = _warnings(registry_audit=registry_audit, mapping_audit=mapping_audit)
    can_promote = not blockers
    return {
        "version": "narrative-mapping-trust-audit-v1",
        "generated_at": _utc_now(),
        "status": "passed" if can_promote else "blocked",
        "summary": {
            "narrative_count": registry_audit["narrative_count"],
            "mapping_count": mapping_audit["mapping_count"],
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
            "trusted_mapping_count": mapping_audit["trusted_mapping_count"],
        },
        "methodology": {
            "name": "Narrative Mapping Methodology v0",
            "required_layers": [
                "股票事实层",
                "候选叙事生成",
                "映射打分",
                "反例和排除",
                "人工审核入口",
            ],
        },
        "registry_audit": registry_audit,
        "mapping_audit": mapping_audit,
        "blockers": blockers,
        "warnings": warnings,
        "promotion_decision": {
            "can_promote_to_trusted": can_promote,
            "required_next_step": "none" if can_promote else "source_and_logic_audit",
        },
        "disclaimer": (
            "This audit checks whether narrative stores can be promoted to trusted "
            "validated knowledge. It does not create trading signals or predictions."
        ),
    }


def render_html_report(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    methodology = _mapping(report.get("methodology"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>叙事映射可信度审计</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>叙事映射可信度审计</h1>",
            '<section class="summary">',
            _html_kv("审计状态", _status_label(str(report.get("status", "")))),
            _html_kv("生成时间", report.get("generated_at", "")),
            _html_kv("方法论", methodology.get("name", "")),
            "<p>本报告用于检查叙事定义和股票映射是否具备可信升级条件，不构成投资建议、交易策略或预测。</p>",
            "</section>",
            "<section>",
            "<h2>审计概览</h2>",
            '<div class="metrics">',
            _html_metric("叙事数", summary.get("narrative_count", 0)),
            _html_metric("映射数", summary.get("mapping_count", 0)),
            _html_metric("阻塞项", summary.get("blocker_count", 0)),
            _html_metric("警告项", summary.get("warning_count", 0)),
            _html_metric("可信映射", summary.get("trusted_mapping_count", 0)),
            "</div>",
            "</section>",
            _methodology_section(),
            _list_section("阻塞项", report.get("blockers")),
            _list_section("警告项", report.get("warnings")),
            _audit_section("Registry 审计", report.get("registry_audit")),
            _audit_section("Mapping 审计", report.get("mapping_audit")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _registry_audit(payload: dict[str, Any]) -> dict[str, Any]:
    narratives = _list(payload.get("narratives"))
    trust = _mapping(payload.get("trust_metadata"))
    narrative_ids = sorted(
        str(item.get("narrative_id") or "")
        for item in narratives
        if item.get("narrative_id")
    )
    without_evidence = [
        str(item.get("narrative_id") or "")
        for item in narratives
        if not _has_any(item, ("representative_citations", "representative_citation_ids"))
    ]
    without_exclusions = [
        str(item.get("narrative_id") or "")
        for item in narratives
        if not _has_any(item, ("exclusion_criteria", "exclusion_criteria_zh"))
    ]
    return {
        "trust_status": str(trust.get("trust_status") or "unspecified"),
        "trust_note": str(trust.get("trust_note") or ""),
        "narrative_count": len(narratives),
        "narrative_ids": narrative_ids,
        "narrative_without_evidence_count": len(without_evidence),
        "narrative_without_exclusion_count": len(without_exclusions),
        "narratives_without_evidence": without_evidence,
        "narratives_without_exclusions": without_exclusions,
    }


def _mapping_audit(payload: dict[str, Any], narrative_ids: list[str]) -> dict[str, Any]:
    mappings = _list(payload.get("mappings"))
    trust = _mapping(payload.get("trust_metadata"))
    narrative_id_set = set(narrative_ids)
    undefined = sorted(
        {
            str(item.get("narrative_id") or "")
            for item in mappings
            if item.get("narrative_id") and item.get("narrative_id") not in narrative_id_set
        }
    )
    missing_evidence = [
        str(item.get("stock_code") or "")
        for item in mappings
        if not _has_any(item, ("source_evidence", "source_evidence_ids", "evidence_refs"))
    ]
    missing_rationale = [
        str(item.get("stock_code") or "")
        for item in mappings
        if not _has_any(item, ("mapping_rationale", "rationale"))
    ]
    trusted = [
        item
        for item in mappings
        if item.get("source_trust_status") == "trusted_validated"
        or item.get("trust_status") == "trusted_validated"
    ]
    return {
        "trust_status": str(trust.get("trust_status") or "unspecified"),
        "trust_note": str(trust.get("trust_note") or ""),
        "mapping_count": len(mappings),
        "trusted_mapping_count": len(trusted),
        "mapping_without_source_evidence_count": len(missing_evidence),
        "mapping_without_formal_rationale_count": len(missing_rationale),
        "undefined_narrative_ids": undefined,
        "mapping_methods": _count_by(mappings, "method"),
    }


def _blockers(*, registry_audit: dict[str, Any], mapping_audit: dict[str, Any]) -> list[str]:
    blockers = []
    if registry_audit["trust_status"] != "trusted_validated":
        blockers.append(f"registry_{registry_audit['trust_status']}")
    if mapping_audit["trust_status"] != "trusted_validated":
        blockers.append(f"mapping_store_{mapping_audit['trust_status']}")
    if mapping_audit["mapping_without_source_evidence_count"]:
        blockers.append(
            "mapping_source_evidence_missing:"
            f"{mapping_audit['mapping_without_source_evidence_count']}"
        )
    if mapping_audit["mapping_without_formal_rationale_count"]:
        blockers.append(
            "mapping_formal_rationale_missing:"
            f"{mapping_audit['mapping_without_formal_rationale_count']}"
        )
    if mapping_audit["undefined_narrative_ids"]:
        blockers.append(
            "undefined_mapping_narrative_ids:"
            f"{','.join(mapping_audit['undefined_narrative_ids'])}"
        )
    return blockers


def _warnings(*, registry_audit: dict[str, Any], mapping_audit: dict[str, Any]) -> list[str]:
    warnings = []
    if registry_audit["narrative_without_evidence_count"]:
        warnings.append(
            "narrative_evidence_incomplete:"
            f"{registry_audit['narrative_without_evidence_count']}"
        )
    if registry_audit["narrative_without_exclusion_count"]:
        warnings.append(
            "narrative_exclusions_incomplete:"
            f"{registry_audit['narrative_without_exclusion_count']}"
        )
    return warnings


def _methodology_section() -> str:
    rows = [
        ("股票事实层", "主营业务、行业/概念、财报、公告、指数/ETF 成分等事实输入。"),
        ("候选叙事生成", "从重复事实生成候选主题，模型输出只能作为 proposal。"),
        ("映射打分", "业务相关性、证据数量、证据质量、特异性、持久性和时效性。"),
        ("反例和排除", "说明为什么不属于相邻叙事，避免宽泛标签和热点误配。"),
        ("人工审核入口", "candidate_untrusted 经证据和规则审核后才可能进入 trusted_validated。"),
    ]
    items = "".join(f"<li><strong>{_html_text(name)}</strong>: {_html_text(text)}</li>" for name, text in rows)
    return f"<section><h2>方法论 v0</h2><ul>{items}</ul></section>"


def _list_section(title: str, value: Any) -> str:
    rows = [str(item) for item in value] if isinstance(value, list) else []
    if not rows:
        body = '<p class="empty">无。</p>'
    else:
        body = "<ul>" + "".join(f"<li>{_html_text(item)}</li>" for item in rows) + "</ul>"
    return f"<section><h2>{_html_text(title)}</h2>{body}</section>"


def _audit_section(title: str, value: Any) -> str:
    audit = _mapping(value)
    rows = "".join(
        f"<tr><th>{_html_text(key)}</th><td>{_html_text(_cell_value(item))}</td></tr>"
        for key, item in audit.items()
        if key not in {"narrative_ids"}
    )
    return f"<section><h2>{_html_text(title)}</h2><table>{rows}</table></section>"


def _count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "unspecified")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _has_any(row: dict[str, Any], fields: tuple[str, ...]) -> bool:
    for field in fields:
        value = row.get(field)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, dict) and value:
            return True
    return False


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _status_label(status: str) -> str:
    return {"passed": "通过", "blocked": "阻塞"}.get(status, status)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _cell_value(value: Any) -> Any:
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
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
p, li { line-height: 1.65; }
.summary { border-left: 4px solid #f59e0b; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #e6ebf1; padding: 8px; text-align: left; vertical-align: top; }
th { color: #475569; background: #f8fafc; width: 280px; }
.empty { color: #8a94a6; }
""".strip()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
