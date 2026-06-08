from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from html import escape
from typing import Any

SUPPORTED_REVIEW_ACTIONS = {
    "watch",
    "needs_more_evidence",
    "reject",
    "defer",
    "ready_for_trust_preflight",
}
STATE_BY_ACTION = {
    "watch": "watching",
    "needs_more_evidence": "needs_more_evidence",
    "reject": "rejected",
    "defer": "deferred",
    "ready_for_trust_preflight": "ready_for_trust_preflight",
}


def build_empty_review_action_ledger(generated_at: str | None = None) -> dict[str, Any]:
    return _with_summary(
        {
            "version": "source-candidate-review-action-ledger-v1",
            "generated_at": generated_at or _utc_now(),
            "updated_at": generated_at or _utc_now(),
            "contract": {
                "append_only": True,
                "trusted_promotion_allowed": False,
                "multi_user_auth_enabled": False,
                "external_provider_calls_allowed": False,
            },
            "records": [],
        },
        idempotent_replay_count=0,
    )


def append_candidate_review_action(
    *,
    ledger: dict[str, Any],
    review_queue: dict[str, Any],
    action_request: dict[str, Any],
) -> dict[str, Any]:
    _validate_action_request(action_request)
    candidate = _candidate_row(str(action_request["candidate_id"]), review_queue)
    idempotency_key = str(action_request["idempotency_key"])
    existing_records = [record for record in _list(ledger.get("records")) if isinstance(record, dict)]
    if any(record.get("idempotency_key") == idempotency_key for record in existing_records):
        replay_count = _summary_int(ledger, "idempotent_replay_count") + 1
        return _with_summary({**deepcopy(ledger), "records": existing_records}, idempotent_replay_count=replay_count)

    previous_state = _previous_candidate_state(
        candidate_id=str(action_request["candidate_id"]),
        candidate=candidate,
        records=existing_records,
    )
    if previous_state == "rejected":
        raise ValueError("candidate is in terminal rejected state")

    action = str(action_request["action"])
    record = {
        "action_id": _action_id(action_request),
        "candidate_id": str(action_request["candidate_id"]),
        "actor": str(action_request.get("actor") or "reviewer-placeholder"),
        "action": action,
        "reason": str(action_request["reason"]),
        "created_at": str(action_request.get("created_at") or _utc_now()),
        "idempotency_key": idempotency_key,
        "source_artifact_refs": _mapping(action_request.get("source_artifact_refs")),
        "previous_candidate_state": previous_state,
        "new_candidate_state": STATE_BY_ACTION[action],
        "trusted_promotion_allowed": False,
        "candidate_support_class": str(
            _mapping(candidate.get("trust_tier_summary")).get("support_class") or ""
        ),
    }
    result = {
        **deepcopy(ledger),
        "version": "source-candidate-review-action-ledger-v1",
        "updated_at": record["created_at"],
        "records": [*existing_records, record],
    }
    return _with_summary(
        result,
        idempotent_replay_count=_summary_int(ledger, "idempotent_replay_count"),
    )


def render_review_action_ledger_html(ledger: dict[str, Any]) -> str:
    summary = _mapping(ledger.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>候选叙事复核动作流水</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>候选叙事复核动作流水</h1>",
            '<section class="summary">',
            _html_kv("动作总数", summary.get("total_action_count", 0)),
            _html_kv("幂等重放", summary.get("idempotent_replay_count", 0)),
            _html_kv("可信动作数", summary.get("trusted_action_count", 0)),
            "<p>本流水采用追加写入；复核动作不会直接标记为可信叙事。</p>",
            "</section>",
            _records_table(_list(ledger.get("records"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _validate_action_request(action_request: dict[str, Any]) -> None:
    if not isinstance(action_request, dict):
        raise ValueError("review action request must be an object")
    required = {"candidate_id", "action", "reason", "idempotency_key"}
    missing = sorted(required - set(action_request))
    if missing:
        raise ValueError(f"review action request missing fields: {missing}")
    action = str(action_request.get("action") or "")
    if action not in SUPPORTED_REVIEW_ACTIONS:
        raise ValueError(f"unsupported review action: {action}")
    if action in {"approve", "trusted", "promote"}:
        raise ValueError("trusted promotion is not supported by source review ledger")
    for field in required:
        if not str(action_request.get(field) or ""):
            raise ValueError(f"review action request {field} must be non-empty")


def _candidate_row(candidate_id: str, review_queue: dict[str, Any]) -> dict[str, Any]:
    for row in _list(review_queue.get("rows")):
        if isinstance(row, dict) and str(row.get("candidate_id") or "") == candidate_id:
            return row
    raise ValueError(f"candidate_id not found in review queue: {candidate_id}")


def _previous_candidate_state(
    *,
    candidate_id: str,
    candidate: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    for record in reversed(records):
        if str(record.get("candidate_id") or "") == candidate_id:
            return str(record.get("new_candidate_state") or "candidate_untrusted")
    return str(candidate.get("candidate_state") or "candidate_untrusted")


def _with_summary(
    ledger: dict[str, Any], *, idempotent_replay_count: int
) -> dict[str, Any]:
    records = [record for record in _list(ledger.get("records")) if isinstance(record, dict)]
    counts_by_action: dict[str, int] = {}
    for record in records:
        action = str(record.get("action") or "unknown")
        counts_by_action[action] = counts_by_action.get(action, 0) + 1
    return {
        **ledger,
        "summary": {
            "total_action_count": len(records),
            "idempotent_replay_count": idempotent_replay_count,
            "trusted_action_count": sum(
                1 for record in records if record.get("new_candidate_state") == "trusted"
            ),
            "counts_by_action": counts_by_action,
            "latest_action_at": str(records[-1].get("created_at") or "") if records else "",
        },
    }


def _action_id(action_request: dict[str, Any]) -> str:
    candidate_id = str(action_request["candidate_id"])
    action = str(action_request["action"])
    idempotency_key = str(action_request["idempotency_key"])
    digest = hashlib.sha256(f"{candidate_id}|{action}|{idempotency_key}".encode("utf-8")).hexdigest()[:10].upper()
    return f"ACT_{candidate_id}_{digest}"


def _summary_int(ledger: dict[str, Any], key: str) -> int:
    value = _mapping(ledger.get("summary")).get(key)
    return value if isinstance(value, int) else 0


def _records_table(records: list[Any]) -> str:
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in (
            "action_id",
            "candidate_id",
            "动作",
            "状态变化",
            "原因",
            "操作者",
            "时间",
            "证据",
        )
    )
    body = "".join(_record_html(_mapping(record)) for record in records)
    return f"<section><h2>最近动作</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _record_html(record: dict[str, Any]) -> str:
    refs = _mapping(record.get("source_artifact_refs"))
    state_change = f"{record.get('previous_candidate_state')} -> {record.get('new_candidate_state')}"
    return (
        "<tr>"
        f"<td>{_html_text(record.get('action_id'))}</td>"
        f"<td>{_html_text(record.get('candidate_id'))}</td>"
        f"<td>{_html_text(record.get('action'))}</td>"
        f"<td>{_html_text(state_change)}</td>"
        f"<td>{_html_text(record.get('reason'))}</td>"
        f"<td>{_html_text(record.get('actor'))}</td>"
        f"<td>{_html_text(record.get('created_at'))}</td>"
        f"<td>{_html_text(', '.join(str(value) for value in refs.values()))}</td>"
        "</tr>"
    )


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


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
