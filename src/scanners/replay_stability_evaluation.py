from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_replay_stability_evaluation(
    *,
    replay_run: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    source_events = _list(replay_run.get("source_events"))
    radar_snapshots = _list(replay_run.get("radar_snapshots"))
    quality_findings = _list(replay_run.get("quality_findings"))
    formula_versions = _mapping(_mapping(replay_run.get("output_manifest")).get("formula_versions"))
    stale_events = [
        event
        for event in source_events
        if str(_mapping(event).get("published_at") or "")[:10] < "2026-05-15"
    ]
    metrics = [
        _metric(
            "radar_event_count_variability",
            _radar_variability(radar_snapshots),
            "Radar event-count spread across replay snapshots.",
        ),
        _metric(
            "quality_issue_density",
            _ratio(len(quality_findings), max(len(radar_snapshots), 1)),
            "Quality findings per radar snapshot.",
        ),
        _metric(
            "source_freshness_coverage",
            _ratio(len(source_events) - len(stale_events), max(len(source_events), 1)),
            "Share of source events inside the recent freshness band.",
        ),
        _metric(
            "formula_version_coverage",
            len([value for value in formula_versions.values() if str(value)]),
            "Count of declared formula versions used by replay.",
        ),
    ]
    return {
        "version": "replay-stability-evaluation-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "radar_snapshot_count": len(radar_snapshots),
            "quality_finding_count": len(quality_findings),
            "source_event_count": len(source_events),
            "stale_source_event_count": len(stale_events),
            "metric_count": len(metrics),
            "warning_count": 0,
        },
        "contract": {
            "metrics_scope": "system_quality_only",
            "trading_backtest_allowed": False,
            "return_prediction_allowed": False,
            "portfolio_optimization_allowed": False,
        },
        "metrics": metrics,
        "formula_versions": formula_versions,
        "source_window": _mapping(_mapping(replay_run.get("replay_input")).get("window")),
        "warnings": [],
    }


def render_replay_stability_evaluation_html(evaluation: dict[str, Any]) -> str:
    summary = _mapping(evaluation.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>雷达与质量稳定性评估</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>雷达与质量稳定性评估</h1>",
            '<section class="summary">',
            _html_kv("雷达快照", summary.get("radar_snapshot_count", 0)),
            _html_kv("质量发现", summary.get("quality_finding_count", 0)),
            _html_kv("来源事件", summary.get("source_event_count", 0)),
            "<p>这些是系统质量指标，不包含交易回测、收益预测或组合优化。</p>",
            "</section>",
            _metrics_table(_list(evaluation.get("metrics"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _metric(metric_id: str, value: float | int, description: str) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "value": value,
        "description": description,
        "scope": "system_quality",
    }


def _radar_variability(radar_snapshots: list[Any]) -> int:
    counts = [_positive_int(_mapping(snapshot).get("event_count"), default=0) for snapshot in radar_snapshots]
    if not counts:
        return 0
    return max(counts) - min(counts)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4)


def _metrics_table(metrics: list[Any]) -> str:
    rows = [_mapping(metric) for metric in metrics]
    if not rows:
        return "<section><h2>指标</h2><p>没有指标。</p></section>"
    header = "".join(_th(label) for label in ("指标", "数值", "口径"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('metric_id'))}</td>"
        f"<td>{_html_text(row.get('value'))}</td>"
        f"<td>{_html_text(row.get('description'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>指标</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


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
