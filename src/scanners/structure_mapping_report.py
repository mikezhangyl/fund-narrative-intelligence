from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any, Callable


@dataclass(frozen=True)
class StructureMappingReportConfig:
    trade_date: str
    sector_name: str = "机器人"
    index_symbol: str = "000300.SH"
    event_start_date: str | None = None
    event_end_date: str | None = None
    etf_market: str = "cn"
    limit: int = 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_structure_mapping_report(
    *,
    data_source: Any,
    config: StructureMappingReportConfig,
) -> dict[str, Any]:
    event_start = config.event_start_date or config.trade_date
    event_end = config.event_end_date or config.trade_date
    components = {
        "sector_constituents": _list_component(
            capability="sector_constituents",
            operation=lambda: data_source.fetch_sector_constituents(
                sector_name=config.sector_name,
                trade_date=config.trade_date,
                limit=config.limit,
            ),
        ),
        "etf_basic": _list_component(
            capability="etf_basic",
            operation=lambda: data_source.fetch_etf_basic(
                market=config.etf_market,
                limit=config.limit,
            ),
        ),
        "index_constituents": _list_component(
            capability="index_constituents",
            operation=lambda: data_source.fetch_index_constituents(
                index_symbol=config.index_symbol,
                trade_date=config.trade_date,
                limit=config.limit,
            ),
        ),
        "margin_summary": _single_row_component(
            capability="margin_summary",
            operation=lambda: data_source.fetch_margin_summary(
                trade_date=config.trade_date
            ),
        ),
        "margin_detail": _list_component(
            capability="margin_detail",
            operation=lambda: data_source.fetch_margin_detail(
                trade_date=config.trade_date,
                limit=config.limit,
            ),
        ),
        "earnings_calendar": _list_component(
            capability="earnings_calendar",
            operation=lambda: data_source.fetch_earnings_calendar(
                start_date=event_start,
                end_date=event_end,
                limit=config.limit,
            ),
        ),
    }
    data_gaps = _data_gaps(components)
    return {
        "version": "structure-mapping-report-v1",
        "generated_at": _utc_now(),
        "trade_date": config.trade_date,
        "status": _overall_status(components),
        "config": {
            **config.to_dict(),
            "event_start_date": event_start,
            "event_end_date": event_end,
        },
        "summary": _summary(components),
        "data_footprint": _data_footprint(components),
        "data_gaps": data_gaps,
        "data_gap_summary": {
            "gap_count": len(data_gaps),
            "scopes": [gap["scope"] for gap in data_gaps],
        },
        "components": components,
        "degradation_events": list(getattr(data_source, "degradation_events", [])),
        "disclaimer": (
            "Can-Do structure mapping report for observability only; not an "
            "investment recommendation, trading strategy, or prediction."
        ),
    }


def render_html_report(report: dict[str, Any]) -> str:
    components = _mapping(report.get("components"))
    footprint = _mapping(report.get("data_footprint"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>市场结构映射报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>市场结构映射报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", _status_label(str(report.get("status", "")))),
            _html_kv("交易日", report.get("trade_date", "")),
            _html_kv("生成时间", report.get("generated_at", "")),
            "<p>本报告用于观察市场结构映射，不构成投资建议、交易策略或涨跌预测。</p>",
            "</section>",
            '<section class="note">',
            "<h2>阅读说明</h2>",
            "<p>这份报告回答“股票、ETF、指数、板块、杠杆和事件如何连接”。</p>",
            "<p>它只展示已接入数据源的当前样本，不做因果解释或价格预测。</p>",
            "</section>",
            "<section>",
            "<h2>数据调用规模</h2>",
            '<div class="metrics">',
            _html_metric("板块成分行数", footprint.get("sector_constituent_rows", 0)),
            _html_metric("ETF 基础行数", footprint.get("etf_basic_rows", 0)),
            _html_metric("指数成分行数", footprint.get("index_constituent_rows", 0)),
            _html_metric("融资融券摘要行数", footprint.get("margin_summary_rows", 0)),
            _html_metric("融资融券明细行数", footprint.get("margin_detail_rows", 0)),
            _html_metric("事件日历行数", footprint.get("earnings_calendar_rows", 0)),
            _html_metric("合计数据行", footprint.get("total_rows", 0)),
            "</div>",
            "</section>",
            _section(
                "板块成分股",
                _component(components, "sector_constituents"),
                (
                    ("sector_name", "板块"),
                    ("symbol", "代码"),
                    ("name", "名称"),
                    ("pct_change", "涨跌幅"),
                    ("source", "来源"),
                ),
            ),
            _section(
                "ETF 基础信息",
                _component(components, "etf_basic"),
                (
                    ("symbol", "代码"),
                    ("name", "名称"),
                    ("category", "分类"),
                    ("fund_type", "基金类型"),
                    ("tracking_index", "跟踪指数"),
                    ("source", "来源"),
                ),
            ),
            _section(
                "指数成分股",
                _component(components, "index_constituents"),
                (
                    ("index_symbol", "指数"),
                    ("symbol", "代码"),
                    ("name", "名称"),
                    ("weight", "权重"),
                    ("source", "来源"),
                ),
            ),
            _section(
                "融资融券摘要",
                _component(components, "margin_summary"),
                (
                    ("trade_date", "日期"),
                    ("financing_balance", "融资余额"),
                    ("securities_lending_balance", "融券余额"),
                    ("financing_buy_amount", "融资买入额"),
                    ("source", "来源"),
                ),
            ),
            _section(
                "融资融券明细",
                _component(components, "margin_detail"),
                (
                    ("symbol", "代码"),
                    ("name", "名称"),
                    ("financing_balance", "融资余额"),
                    ("financing_buy_amount", "融资买入额"),
                    ("source", "来源"),
                ),
            ),
            _section(
                "事件/公告日历",
                _component(components, "earnings_calendar"),
                (
                    ("ann_date", "日期"),
                    ("symbol", "代码"),
                    ("name", "名称"),
                    ("event_type", "事件"),
                    ("source", "来源"),
                ),
            ),
            _html_data_gaps_section(report.get("data_gaps")),
            _html_failures_section(components),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _list_component(
    *,
    capability: str,
    operation: Callable[[], list[dict[str, Any]]],
) -> dict[str, Any]:
    try:
        rows = [dict(row) for row in operation()]
        return _component_payload(capability=capability, rows=rows)
    except Exception as exc:
        return _component_payload(
            capability=capability,
            rows=[],
            failures=[{"capability": capability, "reason": str(exc)}],
            status="failed",
        )


def _single_row_component(
    *,
    capability: str,
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    try:
        row = dict(operation())
        rows = [row] if row else []
        return _component_payload(capability=capability, rows=rows)
    except Exception as exc:
        return _component_payload(
            capability=capability,
            rows=[],
            failures=[{"capability": capability, "reason": str(exc)}],
            status="failed",
        )


def _component_payload(
    *,
    capability: str,
    rows: list[dict[str, Any]],
    failures: list[dict[str, str]] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    row_status = status or ("completed" if rows else "missing")
    return {
        "capability": capability,
        "status": row_status,
        "row_count": len(rows),
        "source": _first_value(rows, "source"),
        "provider": _first_value(rows, "provider"),
        "rows": rows,
        "failures": list(failures or []),
    }


def _overall_status(components: dict[str, dict[str, Any]]) -> str:
    statuses = [str(component.get("status", "")) for component in components.values()]
    if statuses and all(status == "completed" for status in statuses):
        return "completed"
    if any(status == "completed" for status in statuses):
        return "partial"
    return "failed"


def _summary(components: dict[str, dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(component.get("status", "")) for component in components.values())
    return {
        "component_status_counts": dict(sorted(status_counts.items())),
        "completed_components": [
            key
            for key, component in components.items()
            if component.get("status") == "completed"
        ],
        "failed_components": [
            key
            for key, component in components.items()
            if component.get("status") == "failed"
        ],
    }


def _data_footprint(components: dict[str, dict[str, Any]]) -> dict[str, int]:
    footprint = {
        "sector_constituent_rows": _row_count(components, "sector_constituents"),
        "etf_basic_rows": _row_count(components, "etf_basic"),
        "index_constituent_rows": _row_count(components, "index_constituents"),
        "margin_summary_rows": _row_count(components, "margin_summary"),
        "margin_detail_rows": _row_count(components, "margin_detail"),
        "earnings_calendar_rows": _row_count(components, "earnings_calendar"),
    }
    return {**footprint, "total_rows": sum(footprint.values())}


def _data_gaps(components: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for key, component in components.items():
        status = component.get("status")
        if status == "completed":
            continue
        gaps.append(
            {
                "scope": key,
                "status": status,
                "reason": _gap_reason(component),
            }
        )
    return gaps


def _gap_reason(component: dict[str, Any]) -> str:
    failures = component.get("failures")
    if isinstance(failures, list) and failures:
        first = failures[0]
        if isinstance(first, dict):
            return str(first.get("reason") or "")
    return "no rows returned"


def _row_count(components: dict[str, dict[str, Any]], key: str) -> int:
    return int(_component(components, key).get("row_count") or 0)


def _component(components: dict[str, Any], key: str) -> dict[str, Any]:
    component = components.get(key)
    return component if isinstance(component, dict) else {}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_value(rows: list[dict[str, Any]], field: str) -> str:
    if not rows:
        return ""
    return str(rows[0].get(field) or "")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #2563eb; }
.note { border-left: 4px solid #059669; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; border-radius: 8px; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #e6ebf1; padding: 8px; text-align: left; vertical-align: top; }
th { color: #475569; background: #f8fafc; }
.status { font-weight: 700; }
.empty { color: #8a94a6; }
""".strip()


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _section(
    title: str,
    component: dict[str, Any],
    columns: tuple[tuple[str, str], ...],
) -> str:
    return "\n".join(
        [
            "<section>",
            f"<h2>{_html_text(title)}</h2>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(str(component.get("status", "")))),
            _html_metric("行数", component.get("row_count", 0)),
            _html_metric("数据来源", component.get("source", "")),
            "</div>",
            _rows_table(_rows(component), columns),
            "</section>",
        ]
    )


def _rows_table(rows: list[dict[str, Any]], columns: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return '<p class="empty">没有返回可展示数据。</p>'
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = "".join(f"<td>{_html_text(row.get(field, ''))}</td>" for field, _ in columns)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _html_data_gaps_section(value: Any) -> str:
    gaps = value if isinstance(value, list) else []
    if not gaps:
        return "<section><h2>数据缺口</h2><p>无。</p></section>"
    rows = [
        {
            "scope": gap.get("scope", ""),
            "status": gap.get("status", ""),
            "reason": gap.get("reason", ""),
        }
        for gap in gaps
        if isinstance(gap, dict)
    ]
    return "\n".join(
        [
            "<section>",
            "<h2>数据缺口</h2>",
            _rows_table(
                rows,
                (
                    ("scope", "范围"),
                    ("status", "状态"),
                    ("reason", "原因"),
                ),
            ),
            "</section>",
        ]
    )


def _html_failures_section(components: dict[str, Any]) -> str:
    failures = []
    for key, component in components.items():
        if not isinstance(component, dict):
            continue
        for failure in component.get("failures") or []:
            if isinstance(failure, dict):
                failures.append(
                    {
                        "component": key,
                        "capability": failure.get("capability", ""),
                        "reason": failure.get("reason", ""),
                    }
                )
    if not failures:
        return "<section><h2>失败信息</h2><p>无。</p></section>"
    return "\n".join(
        [
            "<section>",
            "<h2>失败信息</h2>",
            _rows_table(
                failures,
                (
                    ("component", "组件"),
                    ("capability", "能力"),
                    ("reason", "原因"),
                ),
            ),
            "</section>",
        ]
    )


def _rows(component: dict[str, Any]) -> list[dict[str, Any]]:
    rows = component.get("rows")
    return rows if isinstance(rows, list) else []


def _status_label(status: str) -> str:
    return {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "missing": "缺数据",
    }.get(status, status)


def _html_text(value: Any) -> str:
    return escape(str(value or ""))
