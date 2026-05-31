from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "config" / "narrative_source_governance.json"


def load_source_governance_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_source_registry(
    registry_payload: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_policy = policy or load_source_governance_policy()
    decisions = [
        validate_source_registry_entry(entry, policy=active_policy)
        for entry in _list(registry_payload.get("sources"))
    ]
    blocked = [decision for decision in decisions if decision["gate_status"] == "blocked"]
    passed = [decision for decision in decisions if decision["gate_status"] == "passed"]
    return {
        "version": "source-governance-evaluation-v1",
        "policy_version": str(active_policy.get("version") or ""),
        "generated_at": _utc_now(),
        "summary": {
            "source_count": len(decisions),
            "passed_count": len(passed),
            "blocked_count": len(blocked),
            "live_smoke_allowed_count": sum(
                1 for decision in decisions if decision["live_smoke_allowed"]
            ),
        },
        "decisions": decisions,
        "prohibited_behaviors": list(active_policy.get("prohibited_behaviors") or []),
        "disclosure": {
            "owner_boundary": (
                "FNI validates source governance labels; stock-data-gateway owns "
                "upstream acquisition, credentials, rate limits, and crawler safety."
            ),
            "live_smoke_rule": (
                "Crawler sources require robots/TOS review and request pacing policy "
                "before live smoke."
            ),
        },
    }


def validate_source_registry_entry(
    entry: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_policy = policy or load_source_governance_policy()
    missing = _missing_required_fields(entry, active_policy)
    prohibited_hits = _prohibited_behavior_hits(entry, active_policy)
    blocked_reasons: list[str] = []
    if missing:
        blocked_reasons.append("missing_required_registry_field")
    if _owner_service_invalid(entry, active_policy):
        blocked_reasons.append("owner_service_invalid")
    if _is_crawler(entry, active_policy):
        blocked_reasons.extend(_crawler_blocked_reasons(entry))
    if prohibited_hits:
        blocked_reasons.append("prohibited_behavior_declared")
    blocked_reasons = _unique(blocked_reasons)
    return {
        "source_id": str(entry.get("source_id") or ""),
        "display_name": str(entry.get("display_name") or ""),
        "acquisition_mode": str(entry.get("acquisition_mode") or ""),
        "owner_service": str(entry.get("owner_service") or ""),
        "permission_status": str(entry.get("permission_status") or ""),
        "license_scope": str(entry.get("license_scope") or ""),
        "retention_policy": str(entry.get("retention_policy") or ""),
        "redistribution_policy": str(entry.get("redistribution_policy") or ""),
        "anti_bot_risk": str(entry.get("anti_bot_risk") or ""),
        "missing_required_fields": missing,
        "prohibited_behavior_hits": prohibited_hits,
        "blocked_reasons": blocked_reasons,
        "gate_status": "blocked" if blocked_reasons else "passed",
        "live_smoke_allowed": not blocked_reasons,
        "required_before_live_smoke": _required_before_live_smoke(entry, active_policy),
        "allowed_product_use": _strings(entry.get("allowed_product_use")),
    }


def render_source_governance_html(evaluation: dict[str, Any]) -> str:
    summary = _mapping(evaluation.get("summary"))
    rows = "\n".join(_decision_rows(evaluation.get("decisions")))
    prohibited = ", ".join(
        _prohibited_label(code) for code in _strings(evaluation.get("prohibited_behaviors"))
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>来源准入治理报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; }}
    .meta, .notice {{ line-height: 1.6; color: #4b5563; }}
    .notice {{ margin: 16px 0; padding: 12px 14px; border-left: 4px solid #991b1b; background: #fef2f2; color: #7f1d1d; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>来源准入治理报告</h1>
  <div class="meta">
    <div>Policy：<code>{_html_text(evaluation.get("policy_version"))}</code></div>
    <div>来源数：<code>{summary.get("source_count", 0)}</code>，通过：<code>{summary.get("passed_count", 0)}</code>，阻断：<code>{summary.get("blocked_count", 0)}</code></div>
  </div>
  <div class="notice">禁止行为：{_html_text(prohibited)}。Crawler 来源必须先完成 robots/TOS review 和 request pacing policy，才能 live smoke。</div>
  <table>
    <thead><tr><th>source_id</th><th>owner_service</th><th>permission</th><th>license</th><th>retention</th><th>redistribution</th><th>anti_bot</th><th>gate</th><th>blocked_reasons</th><th>prohibited</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def _decision_rows(value: Any) -> list[str]:
    rows = []
    for decision in _list(value):
        rows.append(
            "      <tr>"
            f"<td><code>{_html_text(decision.get('source_id'))}</code></td>"
            f"<td>{_html_text(decision.get('owner_service'))}</td>"
            f"<td>{_html_text(decision.get('permission_status'))}</td>"
            f"<td>{_html_text(decision.get('license_scope'))}</td>"
            f"<td>{_html_text(decision.get('retention_policy'))}</td>"
            f"<td>{_html_text(decision.get('redistribution_policy'))}</td>"
            f"<td>{_html_text(decision.get('anti_bot_risk'))}</td>"
            f"<td><code>{_html_text(decision.get('gate_status'))}</code></td>"
            f"<td>{_html_text(' | '.join(_strings(decision.get('blocked_reasons'))))}</td>"
            f"<td>{_html_text(' | '.join(_strings(decision.get('prohibited_behavior_hits'))))}</td>"
            "</tr>"
        )
    return rows


def _missing_required_fields(entry: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    return [
        field
        for field in _strings(policy.get("required_registry_fields"))
        if field not in entry or entry[field] in ("", None, [])
    ]


def _owner_service_invalid(entry: dict[str, Any], policy: dict[str, Any]) -> bool:
    owner = str(entry.get("owner_service") or "")
    return owner not in set(_strings(policy.get("allowed_owner_services")))


def _is_crawler(entry: dict[str, Any], policy: dict[str, Any]) -> bool:
    return str(entry.get("acquisition_mode") or "") in set(
        _strings(policy.get("crawler_acquisition_modes"))
    )


def _crawler_blocked_reasons(entry: dict[str, Any]) -> list[str]:
    reasons = []
    robots = _mapping(entry.get("robots_tos_review"))
    pacing = _mapping(entry.get("request_pacing_policy"))
    if str(robots.get("status") or "") not in {"approved", "allowed", "not_required_official_api"}:
        reasons.append("robots_tos_review_required")
    if str(pacing.get("status") or "") != "defined":
        reasons.append("request_pacing_policy_required")
    return reasons


def _required_before_live_smoke(entry: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    required = []
    if _is_crawler(entry, policy):
        required.extend(_crawler_blocked_reasons(entry))
    if _prohibited_behavior_hits(entry, policy):
        required.append("remove_prohibited_behaviors")
    return _unique(required)


def _prohibited_behavior_hits(entry: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    prohibited = set(_strings(policy.get("prohibited_behaviors")))
    return [item for item in _strings(entry.get("prohibited_behaviors")) if item in prohibited]


def _prohibited_label(code: str) -> str:
    labels = _mapping(load_source_governance_policy().get("prohibited_behavior_labels"))
    return str(labels.get(code) or code)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
