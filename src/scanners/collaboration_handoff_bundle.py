from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

SECRET_MARKERS = ("secret", "token", "api_key", "password")


def build_collaboration_handoff_bundle(
    *,
    research_export: dict[str, Any],
    quality_audit: dict[str, Any],
    requested_decisions: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    candidates = _candidates(research_export)
    evidence = [_safe_mapping(event) for event in _list(research_export.get("source_events"))]
    notes = [_safe_mapping(note) for note in _list(research_export.get("analyst_notes"))]
    quality_findings = [_safe_mapping(item) for item in _quality_findings(quality_audit)]
    decisions = [_normalize_decision(item) for item in requested_decisions or []]
    audit_trail = _audit_trail(decisions)
    return {
        "version": "collaboration-handoff-bundle-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "candidate_count": len(candidates),
            "evidence_count": len(evidence),
            "note_count": len(notes),
            "quality_finding_count": len(quality_findings),
            "requested_decision_count": len(decisions),
            "audit_event_count": len(audit_trail),
        },
        "role_model": {
            "mode": "local_placeholder",
            "roles": ["reviewer", "pm", "architect", "operator"],
            "external_identity_provider_required": False,
        },
        "governance_policy": {
            "promotion_gate_weakened": False,
            "evidence_required_for_promotion": True,
            "notes_can_promote_trusted_state": False,
            "chat_history_required": False,
        },
        "candidates": candidates,
        "evidence": evidence,
        "analyst_notes": notes,
        "quality_findings": quality_findings,
        "requested_decisions": decisions,
        "audit_trail": audit_trail,
    }


def render_collaboration_handoff_html(bundle: dict[str, Any]) -> str:
    summary = _mapping(bundle.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>协作评审交接包</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>协作评审交接包</h1>",
            '<section class="summary">',
            _html_kv("候选项", summary.get("candidate_count", 0)),
            _html_kv("证据", summary.get("evidence_count", 0)),
            _html_kv("请求决策", summary.get("requested_decision_count", 0)),
            "<p>交接包不依赖聊天记录，不弱化证据要求或可信提升门禁。</p>",
            "</section>",
            _decisions_table(_list(bundle.get("requested_decisions"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _candidates(research_export: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"candidate_id": str(value), "candidate_type": "narrative", "display_name": str(value)}
        for value in _list(research_export.get("narratives"))
        if str(value)
    ]


def _quality_findings(quality_audit: dict[str, Any]) -> list[Any]:
    return _list(
        quality_audit.get("findings")
        or quality_audit.get("issues")
        or quality_audit.get("quality_findings")
    )


def _normalize_decision(item: dict[str, Any]) -> dict[str, Any]:
    row = _safe_mapping(item)
    return {
        "decision_id": str(row.get("decision_id") or ""),
        "decision_type": str(row.get("decision_type") or ""),
        "target_ref": _safe_mapping(row.get("target_ref")),
        "responsible_role": str(row.get("responsible_role") or "reviewer"),
        "rationale": str(row.get("rationale") or ""),
        "status": str(row.get("status") or "requested"),
    }


def _audit_trail(decisions: list[dict[str, Any]]) -> list[dict[str, str]]:
    events = [
        {
            "event_type": "bundle_created",
            "actor_role": "operator",
            "detail": "collaboration handoff bundle generated",
        }
    ]
    events.extend(
        {
            "event_type": "decision_requested",
            "actor_role": decision["responsible_role"],
            "detail": decision["decision_id"],
        }
        for decision in decisions
    )
    events.append(
        {
            "event_type": "promotion_gate_preserved",
            "actor_role": "system",
            "detail": "notes and handoff requests cannot promote trusted state",
        }
    )
    return events


def _safe_mapping(value: Any) -> dict[str, Any]:
    row = _mapping(value)
    return {
        str(key): _safe_value(key, child)
        for key, child in row.items()
        if not _is_secret_key(str(key))
    }


def _safe_value(key: Any, value: Any) -> Any:
    if _is_secret_key(str(key)):
        return None
    if isinstance(value, dict):
        return _safe_mapping(value)
    if isinstance(value, list):
        return [_safe_value(key, item) for item in value]
    text = str(value)
    if any(marker in text.casefold() for marker in SECRET_MARKERS):
        return "[redacted]"
    return value


def _is_secret_key(key: str) -> bool:
    lowered = key.casefold()
    return any(marker in lowered for marker in SECRET_MARKERS)


def _decisions_table(decisions: list[Any]) -> str:
    rows = [_mapping(decision) for decision in decisions]
    if not rows:
        return "<section><h2>请求决策</h2><p>没有请求决策。</p></section>"
    header = "".join(_th(label) for label in ("决策", "类型", "角色", "状态", "理由"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('decision_id'))}</td>"
        f"<td>{_html_text(row.get('decision_type'))}</td>"
        f"<td>{_html_text(row.get('responsible_role'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('rationale'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>请求决策</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


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


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; }
th { background: #eef2f7; font-size: 13px; }
td { font-size: 13px; }
""".strip()
