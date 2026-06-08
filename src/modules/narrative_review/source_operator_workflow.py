from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_source_operator_workflow(
    *,
    fresh_digest: dict[str, Any],
    review_queue: dict[str, Any],
    preflight_index: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    queue_by_topic = _queue_rows_by_topic(review_queue)
    preflights = preflight_index or {}
    items = [
        _workflow_item(
            digest_item=item,
            queue_row=queue_by_topic.get(str(_mapping(item).get("narrative_key") or "")),
            preflight_index=preflights,
        )
        for item in _list(fresh_digest.get("items"))
        if isinstance(item, dict)
    ]
    return {
        "version": "source-operator-workflow-v1",
        "generated_at": generated_at or _utc_now(),
        "status": fresh_digest.get("status", "ok"),
        "summary": {
            "digest_item_count": len(items),
            "linked_candidate_count": sum(1 for item in items if item.get("candidate_id")),
            "degraded_input_count": sum(1 for item in items if item.get("input_state") == "degraded"),
            "trusted_item_count": sum(1 for item in items if item.get("trusted_implied") is True),
        },
        "contract": {
            "hosted_web_app_required": False,
            "auth_required": False,
            "ai_recommendation_allowed": False,
            "trusted_claim_without_preflight_allowed": False,
        },
        "items": items,
    }


def render_source_operator_workflow_html(workflow: dict[str, Any]) -> str:
    summary = _mapping(workflow.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>每日摘要到候选复核工作流</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>每日摘要到候选复核工作流</h1>",
            '<section class="summary">',
            _html_kv("摘要项", summary.get("digest_item_count", 0)),
            _html_kv("已链接候选", summary.get("linked_candidate_count", 0)),
            _html_kv("降级输入", summary.get("degraded_input_count", 0)),
            "<p>本页只提供操作路径，不会暗示可信叙事，也不生成投资建议。</p>",
            "</section>",
            _items_table(_list(workflow.get("items"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _workflow_item(
    *,
    digest_item: dict[str, Any],
    queue_row: dict[str, Any] | None,
    preflight_index: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(_mapping(queue_row).get("candidate_id") or "")
    degradation_flags = _degradation_flags(digest_item, queue_row)
    support_class = str(_mapping(_mapping(queue_row).get("trust_tier_summary")).get("support_class") or "")
    input_state = _input_state(
        candidate_id=candidate_id,
        support_class=support_class,
        degradation_flags=degradation_flags,
    )
    trust_label = str(
        _mapping(digest_item.get("source_quality_metadata")).get("best_trust_tier")
        or _mapping(_mapping(queue_row).get("trust_tier_summary")).get("best_trust_tier")
        or "candidate_untrusted"
    )
    return {
        "digest_item_id": str(digest_item.get("stable_digest_id") or ""),
        "narrative_key": str(digest_item.get("narrative_key") or ""),
        "display_name": str(digest_item.get("display_name") or digest_item.get("narrative_key") or ""),
        "digest_candidate_state": str(digest_item.get("candidate_state") or ""),
        "candidate_id": candidate_id,
        "candidate_state": str(_mapping(queue_row).get("candidate_state") or ""),
        "source_trust_label": trust_label,
        "support_class": support_class,
        "input_state": input_state,
        "degradation_flags": degradation_flags,
        "artifact_links": _artifact_links(candidate_id, queue_row, preflight_index),
        "next_operator_action": _next_operator_action(
            candidate_id=candidate_id,
            support_class=support_class,
            degradation_flags=degradation_flags,
        ),
        "trusted_implied": False,
    }


def _next_operator_action(
    *, candidate_id: str, support_class: str, degradation_flags: list[str]
) -> str:
    if not candidate_id:
        return "request_more_evidence"
    if support_class == "heat_signal_only":
        return "watch"
    if degradation_flags:
        return "request_more_evidence"
    if support_class == "official_fact_backed":
        return "run_trust_preflight"
    if support_class == "context_only":
        return "inspect_evidence"
    return "inspect_evidence"


def _input_state(
    *, candidate_id: str, support_class: str, degradation_flags: list[str]
) -> str:
    if not degradation_flags:
        return "ready"
    if not candidate_id:
        return "degraded"
    if support_class == "heat_signal_only":
        return "ready_with_heat_degradation"
    return "ready_with_degradation"


def _artifact_links(
    candidate_id: str,
    queue_row: dict[str, Any] | None,
    preflight_index: dict[str, Any],
) -> dict[str, str]:
    if not candidate_id:
        return {}
    queue_links = _mapping(_mapping(queue_row).get("artifact_links"))
    preflight = _mapping(preflight_index.get(candidate_id))
    preflight_links = _mapping(preflight.get("artifact_links"))
    links = {
        "queue_html": f"source_candidate_review_queue.html#{candidate_id}",
        "evidence_detail_html": str(queue_links.get("evidence_detail_html") or f"candidate_evidence/{candidate_id}.html"),
    }
    preflight_html = preflight_links.get("html")
    if preflight_html:
        links["trust_preflight_html"] = str(preflight_html)
    else:
        links["trust_preflight_html"] = f"source_trust_preflight/{candidate_id}.html"
    return links


def _queue_rows_by_topic(review_queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("topic") or ""): row
        for row in _list(review_queue.get("rows"))
        if isinstance(row, dict) and str(row.get("topic") or "")
    }


def _degradation_flags(
    digest_item: dict[str, Any], queue_row: dict[str, Any] | None
) -> list[str]:
    values = _strings(digest_item.get("degradation_events"))
    if queue_row is not None:
        values.extend(_strings(queue_row.get("degradation_flags")))
    return _unique(values)


def _items_table(items: list[Any]) -> str:
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in (
            "摘要项",
            "候选",
            "状态",
            "信任标签",
            "降级",
            "下一步",
            "链接",
        )
    )
    body = "".join(_item_html(_mapping(item)) for item in items)
    return f"<section><h2>操作队列</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _item_html(item: dict[str, Any]) -> str:
    links = _mapping(item.get("artifact_links"))
    link_html = "<br>".join(
        f'<a href="{_html_text(url)}">{_html_text(label)}</a>'
        for label, url in links.items()
    )
    return (
        "<tr>"
        f"<td>{_html_text(item.get('display_name'))}</td>"
        f"<td>{_html_text(item.get('candidate_id'))}</td>"
        f"<td>{_html_text(item.get('input_state'))} / {_html_text(item.get('candidate_state'))}</td>"
        f"<td>{_html_text(item.get('source_trust_label'))}</td>"
        f"<td>{_html_text(', '.join(_strings(item.get('degradation_flags'))))}</td>"
        f"<td>{_html_text(item.get('next_operator_action'))}</td>"
        f"<td>{link_html}</td>"
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
a { color: #1d4ed8; }
"""


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


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
