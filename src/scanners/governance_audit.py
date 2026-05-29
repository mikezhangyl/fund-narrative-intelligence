from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "config" / "governance_audit_schema.json"


def load_governance_audit_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_governance_audit_export(
    *,
    record_payload: dict[str, Any],
    service_ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    schema = load_governance_audit_schema()
    approved_ids = set(_strings(_mapping(service_ledger_payload).get("approved_record_ids")))
    records = [
        _audit_record(record, schema=schema, approved_ids=approved_ids)
        for record in _list(record_payload.get("records"))
    ]
    return {
        "version": "governance-audit-export-v1",
        "schema_version": schema["version"],
        "generated_at": _utc_now(),
        "read_only": True,
        "summary": {
            "record_count": len(records),
            "pm_facing_warning_count": sum(
                len(record["pm_facing_warnings"]) for record in records
            ),
            "developer_facing_warning_count": sum(
                len(record["developer_facing_warnings"]) for record in records
            ),
        },
        "records": records,
        "csv_columns": [
            "record_type",
            "record_id",
            "display_name",
            "status",
            "trust_status",
            "human_review_status",
            "source_store",
            "service_ledger_approval_id",
            "warning_codes",
        ],
        "disclaimer": (
            "Governance audit export is read-only and must not mutate narrative, "
            "mapping, evidence, or promotion stores."
        ),
    }


def render_html_report(export: dict[str, Any]) -> str:
    summary = _mapping(export.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>叙事治理审计导出</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>叙事治理审计导出</h1>",
            '<section class="summary">',
            _html_kv("生成时间", export.get("generated_at", "")),
            _html_kv("只读导出", export.get("read_only", "")),
            _html_kv("记录数", summary.get("record_count", 0)),
            _html_kv("PM 可见告警", summary.get("pm_facing_warning_count", 0)),
            _html_kv("开发可见告警", summary.get("developer_facing_warning_count", 0)),
            "</section>",
            _records_table(export.get("records")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _audit_record(
    record: dict[str, Any],
    *,
    schema: dict[str, Any],
    approved_ids: set[str],
) -> dict[str, Any]:
    warning_codes = _warning_codes(record, schema=schema, approved_ids=approved_ids)
    pm_warnings = [
        _pm_warning(code)
        for code in warning_codes
        if code in set(_strings(_mapping(schema.get("warning_policy")).get("pm_facing")))
    ]
    developer_warnings = [
        code
        for code in warning_codes
        if code in set(_strings(_mapping(schema.get("warning_policy")).get("developer_facing")))
    ]
    payload = {
        "record_type": str(record.get("record_type") or ""),
        "record_id": str(record.get("record_id") or ""),
        "display_name": str(record.get("display_name") or ""),
        "status": str(record.get("status") or ""),
        "trust_status": str(record.get("trust_status") or ""),
        "human_review_status": str(record.get("human_review_status") or ""),
        "review_status": str(record.get("review_status") or record.get("human_review_status") or ""),
        "source_store": str(record.get("source_store") or ""),
        "service_ledger_approval_id": str(record.get("service_ledger_approval_id") or ""),
        "source_count": int(record.get("source_count") or 0),
        "promotion_decision": str(record.get("promotion_decision") or ""),
        "missing_gates": _strings(record.get("missing_gates")),
        "latest_reviewer": str(record.get("latest_reviewer") or record.get("reviewed_by") or ""),
        "updated_at": str(record.get("updated_at") or ""),
        "warning_codes": warning_codes,
        "pm_facing_warnings": pm_warnings,
        "developer_facing_warnings": developer_warnings,
    }
    return {**payload, "csv_flat": _csv_flat(payload, schema=schema)}


def _warning_codes(
    record: dict[str, Any],
    *,
    schema: dict[str, Any],
    approved_ids: set[str],
) -> list[str]:
    codes = []
    if str(record.get("record_type") or "") not in set(_strings(schema.get("record_types"))):
        codes.append("unsupported_record_type")
    for field in _strings(schema.get("required_trust_state_fields")):
        if field not in record:
            codes.append("missing_required_trust_state_field")
            break
    if _promoted_looking_without_approval(record, approved_ids=approved_ids):
        codes.append("missing_service_ledger_approval")
    return codes


def _promoted_looking_without_approval(record: dict[str, Any], *, approved_ids: set[str]) -> bool:
    record_id = str(record.get("record_id") or "")
    approval_id = str(record.get("service_ledger_approval_id") or "")
    promoted_looking = (
        str(record.get("status") or "") in {"promoted", "active"}
        and str(record.get("trust_status") or "") == "trusted_validated"
        and str(record.get("human_review_status") or "") == "approved"
    )
    if not promoted_looking:
        return False
    return not approval_id and record_id not in approved_ids


def _csv_flat(record: dict[str, Any], *, schema: dict[str, Any]) -> dict[str, str]:
    separator = str(_mapping(schema.get("csv_flattening")).get("list_separator") or " | ")
    return {
        key: separator.join(str(item) for item in value)
        if isinstance(value, list)
        else str(value or "")
        for key, value in record.items()
        if key not in {"csv_flat", "pm_facing_warnings", "developer_facing_warnings"}
    }


def _pm_warning(code: str) -> str:
    if code == "missing_service_ledger_approval":
        return "Promoted-looking record lacks service-ledger approval."
    return code


def _records_table(value: Any) -> str:
    rows = _list(value)
    if not rows:
        return '<section><h2>审计记录</h2><p class="empty">没有返回可展示数据。</p></section>'
    columns = (
        ("record_type", "记录类型"),
        ("record_id", "记录ID"),
        ("display_name", "名称"),
        ("trust_status", "信任状态"),
        ("pm_facing_warnings", "PM 可见告警"),
        ("developer_facing_warnings", "开发告警"),
    )
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(f"<td>{_html_text(_cell(row.get(key)))}</td>" for key, _ in columns)
            + "</tr>"
        )
    return (
        "<section><h2>审计记录</h2>"
        f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"
        "</section>"
    )


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _cell(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #7c3aed; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }
th { background: #f3f4f6; }
.empty { color: #8a94a6; }
""".strip()
