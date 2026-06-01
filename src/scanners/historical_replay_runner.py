from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from html import escape
from typing import Any


def build_historical_replay_run(
    *,
    replay_input: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    normalized_input = _normalize_input(replay_input)
    window = normalized_input["window"]
    source_events = _bounded(
        [
            _normalize_source_event(event)
            for event in _list(_mapping(artifacts.get("source_events")).get("results"))
            if _in_window(str(event.get("published_at") or event.get("event_time") or ""), window)
        ],
        normalized_input["bounds"]["max_source_events"],
    )
    radar_snapshots = _radar_snapshots(_mapping(artifacts.get("radar_snapshots")))
    quality_findings = _quality_findings(_mapping(artifacts.get("quality")))
    portfolio_alerts = _bounded(
        _list(_mapping(artifacts.get("portfolio_alerts")).get("alerts")),
        normalized_input["bounds"]["max_alerts"],
    )
    warnings = _warnings(normalized_input)
    return {
        "version": "historical-replay-run-v1",
        "generated_at": generated_at or _utc_now(),
        "replay_input": normalized_input,
        "run": {
            "run_id": _run_id(normalized_input),
            "deterministic": True,
            "bounded": True,
            "resumable": True,
            "status": "completed",
            "resume_metadata": {
                "checkpoint_id": normalized_input["resume"]["checkpoint_id"],
                "completed_steps": [
                    "load_artifacts",
                    "filter_window",
                    "summarize_outputs",
                    "write_manifest",
                ],
            },
        },
        "contract": {
            "provider_access_allowed": False,
            "trading_backtest_allowed": False,
            "return_prediction_allowed": False,
            "metrics_scope": "system_quality_only",
        },
        "summary": {
            "input_artifact_count": len(normalized_input["artifacts"]),
            "source_event_count": len(source_events),
            "radar_snapshot_count": len(radar_snapshots),
            "quality_finding_count": len(quality_findings),
            "portfolio_alert_count": len(portfolio_alerts),
            "warning_count": len(warnings),
        },
        "source_events": source_events,
        "radar_snapshots": radar_snapshots,
        "quality_findings": quality_findings,
        "portfolio_alerts": portfolio_alerts,
        "warnings": warnings,
        "output_manifest": {
            "formula_versions": normalized_input["formula_versions"],
            "source_window": window,
            "source_mode": normalized_input["source_mode"],
            "input_artifacts": normalized_input["artifacts"],
            "generated_artifacts": [
                "historical_replay_run.json",
                "historical_replay_run.html",
            ],
        },
    }


def render_historical_replay_html(replay: dict[str, Any]) -> str:
    summary = _mapping(replay.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>历史回放与评估运行</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>历史回放与评估运行</h1>",
            '<section class="summary">',
            _html_kv("来源事件", summary.get("source_event_count", 0)),
            _html_kv("雷达快照", summary.get("radar_snapshot_count", 0)),
            _html_kv("质量发现", summary.get("quality_finding_count", 0)),
            _html_kv("组合告警", summary.get("portfolio_alert_count", 0)),
            "<p>本运行用于系统质量评估，不是交易回测、收益预测或组合优化。</p>",
            "</section>",
            _events_table(_list(replay.get("source_events"))),
            _alerts_table(_list(replay.get("portfolio_alerts"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _normalize_input(replay_input: dict[str, Any]) -> dict[str, Any]:
    window = _mapping(replay_input.get("window"))
    bounds = _mapping(replay_input.get("bounds"))
    resume = _mapping(replay_input.get("resume"))
    return {
        "version": str(replay_input.get("version") or "historical-replay-input-v1"),
        "window": {
            "start_date": str(window.get("start_date") or ""),
            "end_date": str(window.get("end_date") or ""),
        },
        "source_mode": str(replay_input.get("source_mode") or "artifact"),
        "formula_versions": _mapping(replay_input.get("formula_versions")),
        "bounds": {
            "max_source_events": _positive_int(bounds.get("max_source_events"), default=500),
            "max_alerts": _positive_int(bounds.get("max_alerts"), default=200),
        },
        "resume": {
            "checkpoint_id": str(resume.get("checkpoint_id") or "initial"),
            "completed_steps": _strings(resume.get("completed_steps")),
        },
        "artifacts": {
            key: str(value)
            for key, value in _mapping(replay_input.get("artifacts")).items()
            if str(key) and str(value)
        },
    }


def _normalize_source_event(event: Any) -> dict[str, Any]:
    row = _mapping(event)
    return {
        "source_event_id": str(row.get("source_event_id") or row.get("id") or ""),
        "published_at": str(row.get("published_at") or row.get("event_time") or ""),
        "title": str(row.get("title") or row.get("headline") or ""),
        "quality_state": str(row.get("quality_state") or row.get("trust_state") or ""),
    }


def _radar_snapshots(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "snapshot_id": str(item.get("stable_digest_id") or item.get("narrative_key") or index),
            "display_name": str(item.get("display_name") or item.get("narrative_name") or ""),
            "event_count": _positive_int(item.get("event_count"), default=0),
        }
        for index, item in enumerate(_list(payload.get("items") or payload.get("digest_items")))
    ]


def _quality_findings(payload: dict[str, Any]) -> list[Any]:
    return _list(
        payload.get("findings")
        or payload.get("issues")
        or payload.get("quality_issues")
    )


def _warnings(replay_input: dict[str, Any]) -> list[dict[str, str]]:
    warnings = []
    if replay_input["source_mode"] != "artifact":
        warnings.append(
            {
                "code": "UNSUPPORTED_SOURCE_MODE",
                "message": "Historical replay runner only consumes local artifacts in this repo.",
            }
        )
    return warnings


def _in_window(published_at: str, window: dict[str, str]) -> bool:
    day = published_at[:10]
    return bool(day) and window["start_date"] <= day <= window["end_date"]


def _bounded(rows: list[Any], limit: int) -> list[Any]:
    return rows[:limit]


def _run_id(replay_input: dict[str, Any]) -> str:
    raw = json.dumps(replay_input, ensure_ascii=False, sort_keys=True)
    return f"replay_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def _events_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>来源事件</h2><p>窗口内没有来源事件。</p></section>"
    header = "".join(_th(label) for label in ("时间", "事件", "标题", "质量"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('published_at'))}</td>"
        f"<td>{_html_text(row.get('source_event_id'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(row.get('quality_state'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>来源事件</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _alerts_table(alerts: list[Any]) -> str:
    rows = [_mapping(alert) for alert in alerts]
    if not rows:
        return "<section><h2>组合告警</h2><p>没有回放告警。</p></section>"
    header = "".join(_th(label) for label in ("规则", "类型", "叙事", "变化"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('rule_id'))}</td>"
        f"<td>{_html_text(row.get('alert_type'))}</td>"
        f"<td>{_html_text(row.get('narrative_name'))}</td>"
        f"<td>{_html_text(row.get('delta'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>组合告警</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


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


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 0)


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
