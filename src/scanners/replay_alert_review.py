from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from html import escape
from typing import Any


def build_replay_alert_review(
    *,
    replay_run: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    alerts = [_mapping(alert) for alert in _list(replay_run.get("portfolio_alerts"))]
    repeated = _repeated_rule_ids(alerts)
    disabled_candidates = _dedupe_noise_reviews(
        [
            _noise_review(alert)
            for alert in alerts
            if _is_small_delta(alert) or str(alert.get("rule_id")) in repeated
        ]
    )
    return {
        "version": "replay-alert-review-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "alert_count": len(alerts),
            "repeated_trigger_count": len(repeated),
            "disabled_threshold_candidate_count": len(disabled_candidates),
            "missed_change_candidate_count": 0,
            "warning_count": len(_list(replay_run.get("warnings"))),
        },
        "contract": {
            "feedback_scope": "system-quality feedback",
            "trading_performance_allowed": False,
            "provider_access_allowed": False,
        },
        "job_storage_contract": {
            "status_values": ["pending", "running", "completed", "failed", "resumable"],
            "stores_progress": True,
            "stores_resume_metadata": True,
            "stores_failure_reason": True,
            "current_production_state_mutation_allowed": False,
        },
        "alerts": alerts,
        "noise_reviews": disabled_candidates,
        "job_snapshot": {
            "run_id": str(_mapping(replay_run.get("run")).get("run_id") or ""),
            "status": str(_mapping(replay_run.get("run")).get("status") or ""),
            "resume_metadata": _mapping(_mapping(replay_run.get("run")).get("resume_metadata")),
            "generated_artifacts": _list(_mapping(replay_run.get("output_manifest")).get("generated_artifacts")),
        },
    }


def render_replay_alert_review_html(review: dict[str, Any]) -> str:
    summary = _mapping(review.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>历史告警有效性与噪声复盘</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>历史告警有效性与噪声复盘</h1>",
            '<section class="summary">',
            _html_kv("告警", summary.get("alert_count", 0)),
            _html_kv("重复触发规则", summary.get("repeated_trigger_count", 0)),
            _html_kv("阈值复核候选", summary.get("disabled_threshold_candidate_count", 0)),
            "<p>输出是系统质量反馈，不评价交易表现。</p>",
            "</section>",
            _noise_table(_list(review.get("noise_reviews"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _repeated_rule_ids(alerts: list[dict[str, Any]]) -> set[str]:
    counts = Counter(str(alert.get("rule_id") or "") for alert in alerts)
    return {rule_id for rule_id, count in counts.items() if rule_id and count > 1}


def _is_small_delta(alert: dict[str, Any]) -> bool:
    try:
        return abs(float(alert.get("delta"))) < 0.05
    except (TypeError, ValueError):
        return False


def _noise_review(alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": str(alert.get("rule_id") or ""),
        "alert_type": str(alert.get("alert_type") or ""),
        "narrative_name": str(alert.get("narrative_name") or ""),
        "delta": alert.get("delta"),
        "recommendation": "review_threshold",
        "reason": "repeated trigger or low-magnitude replay delta",
    }


def _dedupe_noise_reviews(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        deduped.setdefault(row["rule_id"], row)
    return list(deduped.values())


def _noise_table(noise_reviews: list[Any]) -> str:
    rows = [_mapping(row) for row in noise_reviews]
    if not rows:
        return "<section><h2>噪声复核</h2><p>没有阈值复核候选。</p></section>"
    header = "".join(_th(label) for label in ("规则", "类型", "叙事", "变化", "建议"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('rule_id'))}</td>"
        f"<td>{_html_text(row.get('alert_type'))}</td>"
        f"<td>{_html_text(row.get('narrative_name'))}</td>"
        f"<td>{_html_text(row.get('delta'))}</td>"
        f"<td>{_html_text(row.get('recommendation'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>噪声复核</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


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
