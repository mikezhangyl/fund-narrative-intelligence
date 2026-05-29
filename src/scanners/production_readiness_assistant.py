from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

AUTHORITATIVE_SOURCES = [
    "deterministic_scores",
    "source_evidence",
    "review_state",
    "promotion_ledger",
]

SECRET_KEY_PARTS = ("secret", "token", "password", "credential", "api_key")


def build_production_readiness_assistant(
    *,
    payload: dict[str, Any],
    as_of: str | None = None,
    ai_enabled: bool = True,
) -> dict[str, Any]:
    generated_at = as_of or _utc_now()
    sanitized = _sanitize(payload)
    services = _services(sanitized.get("services"))
    freshness = _freshness_rows(
        sanitized.get("datasets"),
        as_of=generated_at,
    )
    runbook_actions = _runbook_actions(services)
    ai_assistance = _ai_assistance(
        sanitized.get("ai_summary_inputs"),
        enabled=ai_enabled,
    )
    feedback = _feedback_rows(sanitized.get("feedback"), as_of=generated_at)
    return {
        "version": "production-readiness-assisted-intelligence-v1",
        "generated_at": generated_at,
        "summary": {
            "service_count": len(services),
            "unhealthy_service_count": sum(
                1 for service in services if service["health_status"] == "failed"
            ),
            "dataset_count": len(freshness),
            "freshness_breach_count": sum(1 for row in freshness if row["breach"]),
            "runbook_action_count": len(runbook_actions),
            "ai_summary_count": len(ai_assistance["summaries"]),
            "feedback_count": len(feedback),
            "open_feedback_count": sum(1 for row in feedback if row["status"] == "open"),
        },
        "services": services,
        "freshness": freshness,
        "runbook_actions": runbook_actions,
        "ai_assistance": ai_assistance,
        "feedback": feedback,
        "access_governance": {
            "role_model_placeholder": ["operator", "analyst", "reviewer", "admin"],
            "feedback_mutates_trusted_state": False,
            "future_authz_boundary": "Feedback creates review inputs; trusted state changes remain gated by review/promote workflows.",
        },
        "authoritative_sources": AUTHORITATIVE_SOURCES,
        "disclaimer": (
            "AI assistance is explanatory only. Deterministic scores, source evidence, "
            "review state, and promotion ledgers remain authoritative."
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
            "<title>生产就绪与辅助智能看板</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>生产就绪与辅助智能看板</h1>",
            '<section class="summary">',
            _html_kv("生成时间", report.get("generated_at", "")),
            "<p>AI 不能设置评分、信任状态或推广状态；确定性评分、来源证据、评审状态和推广台账仍是权威依据。</p>",
            "</section>",
            "<section>",
            "<h2>概览</h2>",
            '<div class="metrics">',
            _html_metric("服务", summary.get("service_count", 0)),
            _html_metric("失败服务", summary.get("unhealthy_service_count", 0)),
            _html_metric("数据集", summary.get("dataset_count", 0)),
            _html_metric("SLA 违约", summary.get("freshness_breach_count", 0)),
            _html_metric("AI 说明", summary.get("ai_summary_count", 0)),
            _html_metric("反馈", summary.get("feedback_count", 0)),
            "</div>",
            "</section>",
            _services_section(report.get("services")),
            _freshness_section(report.get("freshness")),
            _runbooks_section(report.get("runbook_actions")),
            _ai_section(_mapping(report.get("ai_assistance"))),
            _feedback_section(report.get("feedback")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _services(value: Any) -> list[dict[str, Any]]:
    rows = []
    for item in _list(value):
        raw = _mapping(item)
        latest_run = _mapping(raw.get("latest_run"))
        warnings = [_mapping(warning) for warning in _list(raw.get("warnings"))]
        run_status = str(latest_run.get("status") or "unknown")
        health_status = _health_status(run_status=run_status, warnings=warnings)
        rows.append(
            {
                "service_id": str(raw.get("service_id") or ""),
                "display_name": str(raw.get("display_name") or raw.get("service_id") or ""),
                "owner_service": str(raw.get("owner_service") or ""),
                "health_status": health_status,
                "latest_run": latest_run,
                "warnings": warnings,
                "runbooks": [_mapping(runbook) for runbook in _list(raw.get("runbooks"))],
            }
        )
    return rows


def _health_status(*, run_status: str, warnings: list[dict[str, Any]]) -> str:
    normalized = run_status.lower()
    if normalized in {"failed", "error", "cancelled"}:
        return "failed"
    if warnings or normalized in {"warning", "partial", "degraded"}:
        return "degraded"
    if normalized in {"succeeded", "completed", "ok"}:
        return "healthy"
    return "unknown"


def _freshness_rows(value: Any, *, as_of: str) -> list[dict[str, Any]]:
    rows = []
    now = _parse_datetime(as_of)
    for item in _list(value):
        raw = _mapping(item)
        source_timestamp = str(raw.get("source_timestamp") or "")
        target_hours = _float(raw.get("sla_target_hours"))
        age_hours = _age_hours(now=now, timestamp=source_timestamp)
        degraded_reasons = [str(reason) for reason in _list(raw.get("degraded_reasons"))]
        status, breach = _freshness_status(
            age_hours=age_hours,
            target_hours=target_hours,
            degraded_reasons=degraded_reasons,
        )
        rows.append(
            {
                "dataset_id": str(raw.get("dataset_id") or ""),
                "surface": str(raw.get("surface") or raw.get("dataset_id") or ""),
                "source_timestamp": source_timestamp,
                "last_successful_run_at": str(raw.get("last_successful_run_at") or ""),
                "sla_target_hours": _rounded(target_hours),
                "age_hours": _rounded(age_hours),
                "freshness_status": status,
                "breach": breach,
                "degraded_reasons": degraded_reasons,
            }
        )
    return rows


def _freshness_status(
    *,
    age_hours: float,
    target_hours: float,
    degraded_reasons: list[str],
) -> tuple[str, bool]:
    if target_hours <= 0:
        return "unknown", False
    if age_hours <= target_hours and not degraded_reasons:
        return "fresh", False
    if "delayed_run" in degraded_reasons:
        return "stale", False
    if age_hours > target_hours:
        return "breached", True
    return "degraded", False


def _runbook_actions(services: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for service in services:
        for runbook in _list(service.get("runbooks")):
            rows.append(
                {
                    "service_id": str(service.get("service_id") or ""),
                    "owner_service": str(service.get("owner_service") or ""),
                    "category": str(_mapping(runbook).get("category") or ""),
                    "title": str(_mapping(runbook).get("title") or ""),
                    "href": str(_mapping(runbook).get("href") or ""),
                }
            )
    return rows


def _ai_assistance(value: Any, *, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "summaries": [],
            "disabled_reason": "AI assistance disabled by operator setting.",
            "safety_contract": _ai_safety_contract(),
        }
    return {
        "enabled": True,
        "summaries": [_summary_row(item) for item in _list(value)],
        "disabled_reason": "",
        "safety_contract": _ai_safety_contract(),
    }


def _summary_row(item: Any) -> dict[str, Any]:
    raw = _mapping(item)
    evidence_ids = [str(value) for value in _list(raw.get("evidence_ids"))]
    source_ids = [str(value) for value in _list(raw.get("source_ids"))]
    return {
        "summary_id": str(raw.get("summary_id") or ""),
        "object_type": str(raw.get("object_type") or ""),
        "object_id": str(raw.get("object_id") or ""),
        "label": "AI assisted explanation",
        "text": str(raw.get("text") or ""),
        "citations": [*evidence_ids, *source_ids],
        "evidence_ids": evidence_ids,
        "source_ids": source_ids,
        "score_component_ids": [str(value) for value in _list(raw.get("score_component_ids"))],
        "model": str(raw.get("model") or ""),
        "prompt_version": str(raw.get("prompt_version") or ""),
        "can_set_trust_state": False,
        "can_set_score": False,
        "can_set_promotion_status": False,
    }


def _ai_safety_contract() -> dict[str, Any]:
    return {
        "explanatory_only": True,
        "requires_citations": True,
        "can_set_trust_state": False,
        "can_set_score": False,
        "can_set_promotion_status": False,
        "disable_supported": True,
    }


def _feedback_rows(value: Any, *, as_of: str) -> list[dict[str, Any]]:
    rows = []
    for item in _list(value):
        raw = _mapping(item)
        feedback_id = str(raw.get("feedback_id") or "")
        rows.append(
            {
                "feedback_id": feedback_id,
                "type": str(raw.get("type") or ""),
                "severity": str(raw.get("severity") or ""),
                "status": str(raw.get("status") or "open"),
                "linked_object": _mapping(raw.get("linked_object")),
                "reviewer": _mapping(raw.get("reviewer")),
                "can_mutate_trusted_state": False,
                "review_queue_input": True,
                "audit_trail": [
                    {
                        "action": "submitted",
                        "at": as_of,
                        "feedback_id": feedback_id,
                    }
                ],
            }
        )
    return rows


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_string = str(key)
            if any(part in key_string.lower() for part in SECRET_KEY_PARTS):
                continue
            sanitized[key_string] = _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _services_section(value: Any) -> str:
    return _rows_section(
        "服务健康",
        value,
        (
            ("service_id", "服务"),
            ("owner_service", "归属"),
            ("health_status", "状态"),
            ("warnings", "告警"),
        ),
    )


def _freshness_section(value: Any) -> str:
    return _rows_section(
        "数据新鲜度与 SLA",
        value,
        (
            ("dataset_id", "数据集"),
            ("freshness_status", "状态"),
            ("age_hours", "年龄小时"),
            ("sla_target_hours", "SLA 小时"),
            ("degraded_reasons", "降级原因"),
        ),
    )


def _runbooks_section(value: Any) -> str:
    return _rows_section(
        "Runbook 动作",
        value,
        (
            ("service_id", "服务"),
            ("category", "类别"),
            ("title", "动作"),
            ("href", "链接"),
        ),
    )


def _ai_section(ai_assistance: dict[str, Any]) -> str:
    rows = _list(ai_assistance.get("summaries"))
    if not ai_assistance.get("enabled"):
        rows = [
            {
                "summary_id": "disabled",
                "object_id": "",
                "label": "disabled",
                "citations": "",
                "text": ai_assistance.get("disabled_reason", ""),
            }
        ]
    return _rows_section(
        "AI 辅助说明",
        rows,
        (
            ("summary_id", "ID"),
            ("object_id", "对象"),
            ("label", "标签"),
            ("citations", "引用"),
            ("text", "说明"),
        ),
    )


def _feedback_section(value: Any) -> str:
    return _rows_section(
        "反馈与治理",
        value,
        (
            ("feedback_id", "反馈 ID"),
            ("type", "类型"),
            ("severity", "严重度"),
            ("status", "状态"),
            ("can_mutate_trusted_state", "可直接改信任状态"),
        ),
    )


def _rows_section(
    title: str,
    value: Any,
    columns: tuple[tuple[str, str], ...],
) -> str:
    rows = [_mapping(row) for row in _list(value)]
    if not rows:
        return f"<section><h2>{_html_text(title)}</h2><p class=\"empty\">没有返回可展示数据。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_html_text(_cell(row.get(key)))}</td>" for key, _ in columns)
        + "</tr>"
        for row in rows
    )
    return f"<section><h2>{_html_text(title)}</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_html_text(label)}</span><strong>{_html_text(value)}</strong></div>'


def _html_styles() -> str:
    return """
body { margin: 0; background: #f7f8fa; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.metric { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 12px; }
.metric span { display: block; color: #52606d; font-size: 13px; }
.metric strong { display: block; margin-top: 6px; font-size: 22px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
.empty { color: #52606d; }
"""


def _age_hours(*, now: datetime | None, timestamp: str) -> float:
    parsed = _parse_datetime(timestamp)
    if now is None or parsed is None:
        return 0.0
    return max((now - parsed).total_seconds() / 3600, 0.0)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _cell(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value or "")


def _html_text(value: Any) -> str:
    return escape(_cell(value), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _rounded(value: float) -> float:
    return round(value, 4)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
