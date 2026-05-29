from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_fund_narrative_change_report(
    *,
    previous_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    delta_threshold: float = 0.02,
    concentration_threshold: float = 0.35,
) -> dict[str, Any]:
    _require_same_fund(previous_snapshot, current_snapshot)
    previous = _exposure_index(previous_snapshot)
    current = _exposure_index(current_snapshot)
    added = _added(previous, current)
    removed = _removed(previous, current)
    increased, decreased = _changed(
        previous,
        current,
        delta_threshold=delta_threshold,
    )
    concentration_changes = [
        item
        for item in increased
        if item["current_exposure"] >= concentration_threshold
    ]
    data_gaps = [
        *_data_gaps(previous_snapshot, snapshot_label="previous"),
        *_data_gaps(current_snapshot, snapshot_label="current"),
    ]
    return {
        "version": "fund-narrative-change-monitor-v1",
        "generated_at": _utc_now(),
        "status": "partial" if data_gaps else "completed",
        "fund": _mapping(current_snapshot.get("fund")),
        "snapshot_window": {
            "previous_as_of_date": str(previous_snapshot.get("as_of_date") or ""),
            "current_as_of_date": str(current_snapshot.get("as_of_date") or ""),
        },
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "increased_count": len(increased),
            "decreased_count": len(decreased),
            "concentration_change_count": len(concentration_changes),
            "data_gap_count": len(data_gaps),
        },
        "source_disclosure": {
            "holding_source": _mapping(current_snapshot.get("holding_source")),
            "previous_holding_source": _mapping(previous_snapshot.get("holding_source")),
            "narrative_source": _mapping(current_snapshot.get("narrative_source")),
            "previous_narrative_source": _mapping(previous_snapshot.get("narrative_source")),
            "mapping_trust_state": str(current_snapshot.get("mapping_trust_state") or ""),
        },
        "added_narratives": added,
        "removed_narratives": removed,
        "increased_narratives": increased,
        "decreased_narratives": decreased,
        "concentration_changes": concentration_changes,
        "data_gaps": data_gaps,
        "disclaimer": (
            "Fund narrative change monitor is for exposure observability only; "
            "it is not investment advice, trading guidance, price prediction, "
            "or an automatic causality claim."
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
            "<title>基金叙事变化监控报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>基金叙事变化监控报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", report.get("status", "")),
            _html_kv("生成时间", report.get("generated_at", "")),
            _html_kv("基金", _fund_label(report.get("fund"))),
            _source_notice(report.get("source_disclosure")),
            "<p>本报告只用于观察基金叙事暴露变化，不构成投资建议、交易策略、价格预测或因果判断。</p>",
            "</section>",
            "<section>",
            "<h2>变化概览</h2>",
            '<div class="metrics">',
            _html_metric("新增叙事", summary.get("added_count", 0)),
            _html_metric("淡出叙事", summary.get("removed_count", 0)),
            _html_metric("暴露上升", summary.get("increased_count", 0)),
            _html_metric("暴露下降", summary.get("decreased_count", 0)),
            _html_metric("集中度变化", summary.get("concentration_change_count", 0)),
            _html_metric("数据缺口", summary.get("data_gap_count", 0)),
            "</div>",
            "</section>",
            _rows_section("新增叙事", report.get("added_narratives"), _change_columns()),
            _rows_section("淡出叙事", report.get("removed_narratives"), _change_columns()),
            _rows_section("暴露上升", report.get("increased_narratives"), _change_columns()),
            _rows_section("暴露下降", report.get("decreased_narratives"), _change_columns()),
            _rows_section("集中度变化", report.get("concentration_changes"), _change_columns()),
            _rows_section(
                "数据缺口",
                report.get("data_gaps"),
                (
                    ("snapshot", "快照"),
                    ("scope", "范围"),
                    ("reason", "说明"),
                ),
            ),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _added(previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _change_row(narrative_id, previous.get(narrative_id), current[narrative_id])
        for narrative_id in sorted(set(current) - set(previous))
    ]


def _removed(previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _change_row(narrative_id, previous[narrative_id], current.get(narrative_id))
        for narrative_id in sorted(set(previous) - set(current))
    ]


def _changed(
    previous: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
    *,
    delta_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    increased = []
    decreased = []
    for narrative_id in sorted(set(previous) & set(current)):
        row = _change_row(narrative_id, previous[narrative_id], current[narrative_id])
        if row["delta"] >= delta_threshold:
            increased.append(row)
        elif row["delta"] <= -delta_threshold:
            decreased.append(row)
    return (
        sorted(increased, key=lambda item: item["delta"], reverse=True),
        sorted(decreased, key=lambda item: item["delta"]),
    )


def _change_row(
    narrative_id: str,
    previous: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> dict[str, Any]:
    previous_exposure = _float(previous.get("raw_exposure")) if previous else 0.0
    current_exposure = _float(current.get("raw_exposure")) if current else 0.0
    payload = current or previous or {}
    return {
        "narrative_id": narrative_id,
        "narrative_name": str(payload.get("narrative_name") or payload.get("display_name") or narrative_id),
        "previous_exposure": _rounded(previous_exposure),
        "current_exposure": _rounded(current_exposure),
        "delta": _rounded(current_exposure - previous_exposure),
    }


def _exposure_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index = {}
    for item in _list(snapshot.get("narrative_exposures")):
        narrative_id = str(item.get("narrative_id") or "")
        if narrative_id:
            index[narrative_id] = item
    return index


def _data_gaps(snapshot: dict[str, Any], *, snapshot_label: str) -> list[dict[str, str]]:
    return [
        {
            "snapshot": snapshot_label,
            "scope": str(item.get("scope") or ""),
            "reason": str(item.get("reason") or ""),
        }
        for item in _list(snapshot.get("data_gaps"))
    ]


def _require_same_fund(previous_snapshot: dict[str, Any], current_snapshot: dict[str, Any]) -> None:
    previous_code = str(_mapping(previous_snapshot.get("fund")).get("fund_code") or "")
    current_code = str(_mapping(current_snapshot.get("fund")).get("fund_code") or "")
    if not previous_code or previous_code != current_code:
        raise ValueError("previous and current snapshots must use the same fund_code")


def _rows_section(
    title: str,
    value: Any,
    columns: tuple[tuple[str, str], ...],
) -> str:
    rows = _list(value)
    if not rows:
        return f"<section><h2>{_html_text(title)}</h2><p class=\"empty\">没有返回可展示数据。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_html_text(_cell(row.get(key)))}</td>" for key, _ in columns)
        + "</tr>"
        for row in rows
    )
    return (
        f"<section><h2>{_html_text(title)}</h2>"
        f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"
    )


def _change_columns() -> tuple[tuple[str, str], ...]:
    return (
        ("narrative_name", "叙事"),
        ("previous_exposure", "前期暴露"),
        ("current_exposure", "当前暴露"),
        ("delta", "变化"),
    )


def _source_notice(value: Any) -> str:
    disclosure = _mapping(value)
    holding_source = _mapping(disclosure.get("holding_source"))
    narrative_source = _mapping(disclosure.get("narrative_source"))
    return "\n".join(
        [
            "<p><strong>持仓来源:</strong> "
            f"{_html_text(holding_source.get('provider'))} / {_html_text(holding_source.get('data_quality'))}</p>",
            "<p><strong>叙事来源:</strong> "
            f"{_html_text(narrative_source.get('source'))} / {_html_text(narrative_source.get('provider'))}</p>",
            "<p><strong>映射信任状态:</strong> "
            f"{_html_text(disclosure.get('mapping_trust_state'))}</p>",
        ]
    )


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _fund_label(value: Any) -> str:
    fund = _mapping(value)
    return f"{fund.get('fund_name', '')} ({fund.get('fund_code', '')})"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _cell(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #2563eb; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }
th { background: #f3f4f6; }
.empty { color: #8a94a6; }
""".strip()
