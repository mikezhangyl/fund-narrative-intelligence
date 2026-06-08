from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_m21_acceptance_report(
    *,
    artifacts: dict[str, dict[str, Any]],
    verification_commands: list[str],
    generated_at: str | None = None,
) -> dict[str, Any]:
    live_probe = _payload(artifacts, "live_probe")
    fixture_probe = _payload(artifacts, "fixture_probe")
    queue = _payload(artifacts, "queue")
    ledger = _payload(artifacts, "ledger")
    preflight = _payload(artifacts, "preflight")
    workflow = _payload(artifacts, "workflow")
    status_buckets = _status_buckets(
        live_probe=live_probe,
        fixture_probe=fixture_probe,
        queue=queue,
        ledger=ledger,
        preflight=preflight,
        workflow=workflow,
    )
    return {
        "version": "m21-source-derived-candidate-acceptance-v1",
        "generated_at": generated_at or _utc_now(),
        "artifact_references": _artifact_references(artifacts),
        "verification_commands": verification_commands,
        "status_buckets": status_buckets,
        "coverage_matrix": {
            "source_kinds": _source_kind_matrix(live_probe),
            "candidate_states": _candidate_state_matrix(queue),
        },
        "live_smoke_summary": _mapping(live_probe.get("summary")),
        "fixture_summary": _mapping(fixture_probe.get("summary")),
        "candidate_queue_summary": _mapping(queue.get("summary")),
        "evidence_summary": _mapping(_payload(artifacts, "evidence").get("summary")),
        "review_ledger_summary": _mapping(ledger.get("summary")),
        "trust_preflight_status": str(preflight.get("overall_status") or "not_available"),
        "operator_workflow_summary": _mapping(workflow.get("summary")),
        "known_degraded_sources": _known_degraded_sources(live_probe),
        "risks": _risks(preflight=preflight, live_probe=live_probe),
        "recommended_next_stories": [
            {
                "owner": "Gateway",
                "recommendation": "Add explicit owner_service in narrative source-event meta if PM wants Gateway-origin ownership visible at response level.",
            },
            {
                "owner": "FNI",
                "recommendation": "Generate evidence and preflight artifacts for every visible queue candidate, not only the reviewed candidate.",
            },
            {
                "owner": "Narrative Service",
                "recommendation": "Define how reviewed source-derived candidates enter the service review state without automatic trust promotion.",
            },
        ],
        "decision": _decision(status_buckets),
        "disclosure": {
            "investment_recommendation_made": False,
            "trusted_or_predictive_claims_made": False,
            "automatic_promotion_performed": False,
        },
    }


def render_m21_acceptance_report_html(report: dict[str, Any]) -> str:
    decision = _mapping(report.get("decision"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>M21 来源候选叙事验收报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>M21 来源候选叙事验收报告</h1>",
            '<section class="summary">',
            _html_kv("PM/Architect 决策", decision.get("pm_architect_decision")),
            f"<p>{_html_text(decision.get('merge_language_zh'))}</p>",
            "<p>本报告不构成投资建议，不会声称候选叙事已经可信或可预测。</p>",
            "</section>",
            _status_buckets_section(_mapping(report.get("status_buckets"))),
            _coverage_section(_mapping(report.get("coverage_matrix"))),
            _artifact_section(_mapping(report.get("artifact_references"))),
            _commands_section(_strings(report.get("verification_commands"))),
            _risks_section(_strings(report.get("risks"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _status_buckets(
    *,
    live_probe: dict[str, Any],
    fixture_probe: dict[str, Any],
    queue: dict[str, Any],
    ledger: dict[str, Any],
    preflight: dict[str, Any],
    workflow: dict[str, Any],
) -> dict[str, list[str]]:
    live_blocking = _int(_mapping(live_probe.get("summary")).get("blocking_source_kinds"))
    fixture_blocking = _int(_mapping(fixture_probe.get("summary")).get("blocking_source_kinds"))
    queue_count = _int(_mapping(queue.get("summary")).get("visible_count"))
    ledger_count = _int(_mapping(ledger.get("summary")).get("total_action_count"))
    workflow_count = _int(_mapping(workflow.get("summary")).get("linked_candidate_count"))
    preflight_status = str(preflight.get("overall_status") or "")
    can_do = []
    degraded = []
    blocked = []
    fixture_only = []
    if live_blocking:
        blocked.append("live_gateway_source_event_acceptance")
    else:
        can_do.append("live_gateway_source_event_acceptance")
    if fixture_blocking and not live_blocking:
        blocked.append("fixture_gateway_source_event_acceptance")
    elif not fixture_blocking:
        pass
    else:
        fixture_only.append("fixture_gateway_source_event_acceptance")
    if queue_count:
        can_do.append("source_candidate_review_queue")
    if _int(_mapping(_payload_from_optional(live_probe)).get("unused")):
        fixture_only.append("unused")
    can_do.append("candidate_evidence_drilldown")
    if ledger_count:
        can_do.append("review_action_ledger")
    if workflow_count:
        can_do.append("operator_workflow")
    if preflight_status == "pass":
        can_do.append("source_trust_preflight")
    elif preflight_status in {"warning", "fail"}:
        degraded.append("source_trust_preflight")
    elif preflight_status:
        fixture_only.append("source_trust_preflight")
    return {
        "can_do": can_do,
        "fixture_only": fixture_only,
        "degraded": degraded,
        "blocked": blocked,
        "not_implemented": ["automatic_trusted_promotion"],
    }


def _source_kind_matrix(live_probe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source_kind": str(result.get("source_kind") or ""),
            "acceptance_status": str(result.get("acceptance_status") or result.get("status") or ""),
            "row_count": _int(result.get("row_count")),
        }
        for result in _list(live_probe.get("source_results"))
        if isinstance(result, dict)
    ]


def _candidate_state_matrix(queue: dict[str, Any]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in _list(queue.get("rows")):
        if isinstance(row, dict):
            state = str(row.get("candidate_state") or "unknown")
            counts[state] = counts.get(state, 0) + 1
    return [
        {"candidate_state": state, "count": counts[state]}
        for state in sorted(counts)
    ]


def _known_degraded_sources(live_probe: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for result in _list(live_probe.get("source_results")):
        if not isinstance(result, dict):
            continue
        degradation_events = _strings(result.get("degradation_events"))
        if result.get("acceptance_status") == "degraded" or degradation_events:
            rows.append(
                {
                    "source_kind": str(result.get("source_kind") or ""),
                    "acceptance_status": str(result.get("acceptance_status") or ""),
                    "degradation_events": degradation_events,
                }
            )
    return rows


def _risks(*, preflight: dict[str, Any], live_probe: dict[str, Any]) -> list[str]:
    risks = []
    if str(preflight.get("overall_status") or "") in {"warning", "fail"}:
        risks.append("Trust preflight still has warning/fail criteria; do not promote candidates automatically.")
    if _known_degraded_sources(live_probe):
        risks.append("Some Gateway source kinds are degraded or return no data in live smoke.")
    risks.append("M21 validates reviewability; it does not validate investment outcomes.")
    return risks


def _decision(status_buckets: dict[str, list[str]]) -> dict[str, str]:
    if status_buckets["blocked"]:
        return {
            "pm_architect_decision": "hold_for_fix",
            "merge_language_zh": "建议暂缓进入下一轮，先处理阻塞项。",
        }
    if status_buckets["degraded"]:
        return {
            "pm_architect_decision": "continue_with_warnings",
            "merge_language_zh": "建议进入下一轮，但保留降级来源和 trust preflight warning 作为后续需求。",
        }
    return {
        "pm_architect_decision": "continue",
        "merge_language_zh": "建议进入下一轮，当前 M21 验收项已满足。",
    }


def _artifact_references(artifacts: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    return {
        name: {
            "path": str(item.get("path") or ""),
            "status": "available" if item.get("payload") else "missing",
        }
        for name, item in artifacts.items()
    }


def _payload(artifacts: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    item = artifacts.get(name) or {}
    return _mapping(item.get("payload"))


def _payload_from_optional(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _status_buckets_section(buckets: dict[str, Any]) -> str:
    labels = {
        "can_do": "Can-Do",
        "fixture_only": "Fixture-only",
        "degraded": "降级",
        "blocked": "阻塞",
        "not_implemented": "未实现",
    }
    items = "".join(
        f"<h3>{_html_text(labels.get(key, key))}</h3><p>{_html_text(', '.join(_strings(value)))}</p>"
        for key, value in buckets.items()
    )
    return f"<section><h2>状态分层</h2>{items}</section>"


def _coverage_section(matrix: dict[str, Any]) -> str:
    source_rows = "".join(
        "<tr>"
        f"<td>{_html_text(_mapping(row).get('source_kind'))}</td>"
        f"<td>{_html_text(_mapping(row).get('acceptance_status'))}</td>"
        f"<td>{_html_text(_mapping(row).get('row_count'))}</td>"
        "</tr>"
        for row in _list(matrix.get("source_kinds"))
    )
    candidate_rows = "".join(
        "<tr>"
        f"<td>{_html_text(_mapping(row).get('candidate_state'))}</td>"
        f"<td>{_html_text(_mapping(row).get('count'))}</td>"
        "</tr>"
        for row in _list(matrix.get("candidate_states"))
    )
    return (
        "<section><h2>覆盖矩阵</h2>"
        "<h3>来源类型</h3><table><thead><tr><th>source_kind</th><th>状态</th><th>行数</th></tr></thead>"
        f"<tbody>{source_rows}</tbody></table>"
        "<h3>候选状态</h3><table><thead><tr><th>candidate_state</th><th>数量</th></tr></thead>"
        f"<tbody>{candidate_rows}</tbody></table></section>"
    )


def _artifact_section(refs: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{_html_text(name)}</td>"
        f"<td>{_html_text(_mapping(ref).get('path'))}</td>"
        f"<td>{_html_text(_mapping(ref).get('status'))}</td>"
        "</tr>"
        for name, ref in refs.items()
    )
    return f"<section><h2>产物引用</h2><table><tbody>{rows}</tbody></table></section>"


def _commands_section(commands: list[str]) -> str:
    items = "".join(f"<li><code>{_html_text(command)}</code></li>" for command in commands)
    return f"<section><h2>验证命令</h2><ul>{items}</ul></section>"


def _risks_section(risks: list[str]) -> str:
    items = "".join(f"<li>{_html_text(risk)}</li>" for risk in risks)
    return f"<section><h2>风险</h2><ul>{items}</ul></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
h3 { font-size: 16px; margin: 16px 0 8px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; margin: 8px 0 16px; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
code { background: #eef2f7; padding: 1px 4px; border-radius: 4px; }
"""


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
