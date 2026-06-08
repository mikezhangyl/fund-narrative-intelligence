from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

OFFICIAL_SOURCE_KINDS = {"official_filings", "official_disclosures", "official_sources"}
PASSING_FRESHNESS_STATES = {"new", "accelerating", "persistent"}


def build_source_trust_preflight(
    *,
    candidate_id: str,
    review_queue: dict[str, Any],
    evidence_detail: dict[str, Any],
    action_ledger: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    candidate = _candidate_row(candidate_id, review_queue)
    events = [event for event in _list(evidence_detail.get("events")) if isinstance(event, dict)]
    latest_action_state = _latest_action_state(candidate_id, action_ledger)
    criteria = [
        _official_source_criterion(candidate, events),
        _source_diversity_criterion(events),
        _entity_symbol_criterion(candidate),
        _freshness_criterion(candidate),
        _degradation_criterion(candidate, evidence_detail, events),
        _review_action_criterion(latest_action_state),
        _metadata_criterion(events),
    ]
    overall_status = _overall_status(criteria)
    return {
        "version": "source-trust-preflight-v1",
        "generated_at": generated_at or _utc_now(),
        "candidate_id": candidate_id,
        "overall_status": overall_status,
        "promotion_allowed": False,
        "read_only": True,
        "candidate_snapshot": {
            "title": str(candidate.get("title") or ""),
            "candidate_state": str(candidate.get("candidate_state") or ""),
            "support_class": _support_class(candidate),
            "freshness_state": str(candidate.get("freshness_state") or ""),
            "latest_review_action_state": latest_action_state,
        },
        "criteria": criteria,
        "blocking_reasons": [
            str(criterion["reason_zh"])
            for criterion in criteria
            if criterion["status"] == "fail"
        ],
        "warnings": [
            str(criterion["reason_zh"])
            for criterion in criteria
            if criterion["status"] == "warning"
        ],
        "disclosure": {
            "automatic_promotion_allowed": False,
            "llm_judgment_allowed": False,
            "investment_conclusion_allowed": False,
        },
    }


def render_source_trust_preflight_html(preflight: dict[str, Any]) -> str:
    snapshot = _mapping(preflight.get("candidate_snapshot"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>候选叙事信任预检</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>候选叙事信任预检</h1>",
            '<section class="summary">',
            _html_kv("候选", snapshot.get("title")),
            _html_kv("总体状态", preflight.get("overall_status")),
            _html_kv("最新复核状态", snapshot.get("latest_review_action_state")),
            "<p>预检只读，不会自动升级为可信叙事，也不构成投资建议。</p>",
            "</section>",
            _criteria_table(_list(preflight.get("criteria"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _official_source_criterion(
    candidate: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    support_class = _support_class(candidate)
    official_count = sum(1 for event in events if event.get("source_kind") in OFFICIAL_SOURCE_KINDS)
    if official_count > 0 and support_class == "official_fact_backed":
        return _criterion(
            "official_or_primary_source",
            "官方或主来源",
            "pass",
            "已有官方或主来源事件支撑候选。",
        )
    if support_class == "heat_signal_only":
        reason = "热度信号不能替代官方或主来源证据。"
    elif support_class == "context_only":
        reason = "上下文证据不能替代官方或主来源证据。"
    else:
        reason = "缺少官方或主来源证据。"
    return _criterion("official_or_primary_source", "官方或主来源", "fail", reason)


def _source_diversity_criterion(events: list[dict[str, Any]]) -> dict[str, Any]:
    source_kinds = sorted({str(event.get("source_kind") or "") for event in events if event.get("source_kind")})
    if len(source_kinds) >= 2:
        return _criterion("source_diversity", "来源多样性", "pass", "至少两个来源类型参与支撑。")
    if len(source_kinds) == 1:
        return _criterion("source_diversity", "来源多样性", "warning", "当前只有一个来源类型，建议继续补充交叉来源。")
    return _criterion("source_diversity", "来源多样性", "fail", "没有可用来源类型。")


def _entity_symbol_criterion(candidate: dict[str, Any]) -> dict[str, Any]:
    symbols = _strings(_mapping(candidate.get("related_entities")).get("symbols"))
    title = str(candidate.get("title") or "")
    if symbols and title:
        return _criterion("entity_symbol_clarity", "实体/符号清晰度", "pass", "候选有明确标题和关联符号。")
    if title:
        return _criterion("entity_symbol_clarity", "实体/符号清晰度", "warning", "候选标题明确，但关联证券符号不足。")
    return _criterion("entity_symbol_clarity", "实体/符号清晰度", "fail", "候选缺少明确标题和实体线索。")


def _freshness_criterion(candidate: dict[str, Any]) -> dict[str, Any]:
    freshness = str(candidate.get("freshness_state") or "")
    if freshness in PASSING_FRESHNESS_STATES:
        return _criterion("freshness", "新鲜度", "pass", "候选处于可复核的新鲜度状态。")
    if freshness in {"cooling", "unknown", ""}:
        return _criterion("freshness", "新鲜度", "warning", "候选新鲜度不足或未知，建议复查时间窗口。")
    return _criterion("freshness", "新鲜度", "fail", "候选处于争议或不可直接预检状态。")


def _degradation_criterion(
    candidate: dict[str, Any],
    evidence_detail: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = _mapping(evidence_detail.get("summary"))
    degraded_count = _int(summary.get("degraded_event_count"))
    missing_count = _int(summary.get("missing_event_count"))
    degradation_flags = _strings(candidate.get("degradation_flags"))
    event_degradations = [
        event_degradation
        for event in events
        for event_degradation in _strings(event.get("degradation_events"))
    ]
    if degraded_count or missing_count or degradation_flags or event_degradations:
        return _criterion(
            "degradation_or_contradiction",
            "降级/矛盾标记",
            "fail",
            "仍存在缺失、降级或矛盾标记，不能进入信任提升。",
        )
    return _criterion("degradation_or_contradiction", "降级/矛盾标记", "pass", "没有发现缺失、降级或矛盾标记。")


def _review_action_criterion(latest_action_state: str) -> dict[str, Any]:
    if latest_action_state == "ready_for_trust_preflight":
        return _criterion("review_action_state", "复核动作状态", "pass", "最近复核动作允许进入 trust preflight。")
    return _criterion(
        "review_action_state",
        "复核动作状态",
        "fail",
        "需要先在 review action ledger 中记录 ready_for_trust_preflight。",
    )


def _metadata_criterion(events: list[dict[str, Any]]) -> dict[str, Any]:
    required = ("source_event_id", "source_url", "event_time", "source_quality")
    missing = [
        f"{event.get('source_event_id') or '<missing>'}.{field}"
        for event in events
        for field in required
        if not str(event.get(field) or "")
    ]
    if missing:
        return _criterion("evidence_metadata", "证据元数据", "fail", "证据缺少必要元数据：" + ", ".join(missing))
    return _criterion("evidence_metadata", "证据元数据", "pass", "证据包含 source_event_id、URL、时间和来源质量。")


def _criterion(
    criterion_id: str,
    label_zh: str,
    status: str,
    reason_zh: str,
) -> dict[str, str]:
    return {
        "criterion_id": criterion_id,
        "label_zh": label_zh,
        "status": status,
        "reason_zh": reason_zh,
        "explanation_zh": f"{label_zh}：{reason_zh}",
    }


def _overall_status(criteria: list[dict[str, Any]]) -> str:
    statuses = {criterion["status"] for criterion in criteria}
    if "fail" in statuses:
        return "fail"
    if "warning" in statuses:
        return "warning"
    return "pass"


def _latest_action_state(candidate_id: str, action_ledger: dict[str, Any]) -> str:
    for record in reversed(_list(action_ledger.get("records"))):
        if isinstance(record, dict) and str(record.get("candidate_id") or "") == candidate_id:
            return str(record.get("new_candidate_state") or "")
    return ""


def _candidate_row(candidate_id: str, review_queue: dict[str, Any]) -> dict[str, Any]:
    for row in _list(review_queue.get("rows")):
        if isinstance(row, dict) and str(row.get("candidate_id") or "") == candidate_id:
            return row
    raise ValueError(f"candidate_id not found in review queue: {candidate_id}")


def _support_class(candidate: dict[str, Any]) -> str:
    return str(_mapping(candidate.get("trust_tier_summary")).get("support_class") or "")


def _criteria_table(criteria: list[Any]) -> str:
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("检查项", "状态", "说明")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(_mapping(criterion).get('label_zh'))}</td>"
        f"<td>{_html_text(_mapping(criterion).get('status'))}</td>"
        f"<td>{_html_text(_mapping(criterion).get('explanation_zh'))}</td>"
        "</tr>"
        for criterion in criteria
    )
    return f"<section><h2>预检标准</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


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
