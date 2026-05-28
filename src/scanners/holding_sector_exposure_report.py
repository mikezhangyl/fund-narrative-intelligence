from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any


@dataclass(frozen=True)
class HoldingSectorExposureConfig:
    symbols: tuple[str, ...]
    trade_date: str
    sector_types: tuple[str, ...] = ("concept",)
    limit_per_symbol: int = 50
    sector_universe_limit: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_holding_sector_exposure_report(
    *,
    data_source: Any,
    config: HoldingSectorExposureConfig,
) -> dict[str, Any]:
    symbols = _unique_symbols(config.symbols)
    try:
        rows = [
            dict(row)
            for row in data_source.fetch_stock_sector_memberships(
                symbols=symbols,
                trade_date=config.trade_date,
                sector_types=list(config.sector_types),
                limit_per_symbol=config.limit_per_symbol,
                sector_universe_limit=config.sector_universe_limit,
            )
        ]
        covered_symbols = sorted({str(row.get("symbol") or "") for row in rows if row.get("symbol")})
        missing_symbols = [symbol for symbol in symbols if symbol not in set(covered_symbols)]
        data_gaps = _data_gaps(symbols=symbols, missing_symbols=missing_symbols)
        return {
            "version": "holding-sector-exposure-v1",
            "generated_at": _utc_now(),
            "trade_date": config.trade_date,
            "status": _status(rows=rows, missing_symbols=missing_symbols, requested_symbols=symbols),
            "config": {**config.to_dict(), "symbols": symbols},
            "summary": {
                "requested_symbol_count": len(symbols),
                "covered_symbol_count": len(covered_symbols),
                "membership_row_count": len(rows),
                "missing_symbols": missing_symbols,
            },
            "rows": rows,
            "sector_exposures": _sector_exposures(rows),
            "data_gaps": data_gaps,
            "data_gap_summary": {
                "gap_count": len(data_gaps),
                "scopes": [gap["scope"] for gap in data_gaps],
            },
            "degradation_events": list(getattr(data_source, "degradation_events", [])),
            "disclaimer": (
                "Can-Do holding sector exposure report for observability only; "
                "not an investment recommendation, trading strategy, or prediction."
            ),
        }
    except Exception as exc:
        return {
            "version": "holding-sector-exposure-v1",
            "generated_at": _utc_now(),
            "trade_date": config.trade_date,
            "status": "failed",
            "config": {**config.to_dict(), "symbols": symbols},
            "summary": {
                "requested_symbol_count": len(symbols),
                "covered_symbol_count": 0,
                "membership_row_count": 0,
                "missing_symbols": symbols,
            },
            "rows": [],
            "sector_exposures": [],
            "data_gaps": _data_gaps(symbols=symbols, missing_symbols=symbols),
            "data_gap_summary": {"gap_count": 1 if symbols else 0, "scopes": ["symbols"] if symbols else []},
            "degradation_events": list(getattr(data_source, "degradation_events", [])),
            "failures": [{"capability": "stock_sector_membership", "reason": str(exc)}],
            "disclaimer": (
                "Can-Do holding sector exposure report for observability only; "
                "not an investment recommendation, trading strategy, or prediction."
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
            "<title>持仓板块暴露报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>持仓板块暴露报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", _status_label(str(report.get("status", "")))),
            _html_kv("交易日", report.get("trade_date", "")),
            _html_kv("生成时间", report.get("generated_at", "")),
            "<p>本报告用于观察持仓与板块/概念的归属关系，不构成投资建议、交易策略或涨跌预测。</p>",
            "</section>",
            "<section>",
            "<h2>覆盖概览</h2>",
            '<div class="metrics">',
            _html_metric("请求股票数", summary.get("requested_symbol_count", 0)),
            _html_metric("覆盖股票数", summary.get("covered_symbol_count", 0)),
            _html_metric("会员关系行数", summary.get("membership_row_count", 0)),
            _html_metric("缺失股票", ", ".join(summary.get("missing_symbols") or []) or "无"),
            "</div>",
            "</section>",
            _html_exposure_section(report.get("sector_exposures")),
            _html_rows_section(report.get("rows")),
            _html_data_gaps_section(report.get("data_gaps")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _sector_exposures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    names_by_symbol: dict[str, str] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "")
        sector_name = str(row.get("sector_name") or "")
        sector_type = str(row.get("sector_type") or "")
        if not symbol or not sector_name:
            continue
        grouped[(sector_name, sector_type)].add(symbol)
        name = str(row.get("name") or "")
        if name:
            names_by_symbol[symbol] = name
    exposures = []
    for (sector_name, sector_type), symbols in grouped.items():
        sorted_symbols = sorted(symbols)
        exposures.append(
            {
                "sector_name": sector_name,
                "sector_type": sector_type,
                "holding_count": len(sorted_symbols),
                "symbols": sorted_symbols,
                "names": [names_by_symbol.get(symbol, "") for symbol in sorted_symbols],
            }
        )
    return sorted(
        exposures,
        key=lambda row: (-int(row["holding_count"]), str(row["sector_name"])),
    )


def _data_gaps(*, symbols: list[str], missing_symbols: list[str]) -> list[dict[str, Any]]:
    if not missing_symbols:
        return []
    return [
        {
            "scope": "stock_sector_membership_symbols",
            "requested": len(symbols),
            "actual": len(symbols) - len(missing_symbols),
            "missing": len(missing_symbols),
            "reason": "部分股票没有返回板块/概念归属；可能是网关反向索引覆盖不足、上游降级或该股票无可用归属。",
            "missing_symbols": missing_symbols,
        }
    ]


def _status(
    *,
    rows: list[dict[str, Any]],
    missing_symbols: list[str],
    requested_symbols: list[str],
) -> str:
    if rows and not missing_symbols:
        return "completed"
    if rows:
        return "partial"
    if requested_symbols:
        return "missing"
    return "blocked"


def _unique_symbols(symbols: tuple[str, ...]) -> list[str]:
    seen = set()
    ordered = []
    for symbol in symbols:
        normalized = str(symbol).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _html_exposure_section(value: Any) -> str:
    rows = value if isinstance(value, list) else []
    return "\n".join(
        [
            "<section>",
            "<h2>板块暴露汇总</h2>",
            _rows_table(
                rows,
                (
                    ("sector_name", "板块/概念"),
                    ("sector_type", "类型"),
                    ("holding_count", "持仓数"),
                    ("symbols", "股票代码"),
                ),
            ),
            "</section>",
        ]
    )


def _html_rows_section(value: Any) -> str:
    rows = value if isinstance(value, list) else []
    return "\n".join(
        [
            "<section>",
            "<h2>归属明细</h2>",
            _rows_table(
                rows,
                (
                    ("symbol", "代码"),
                    ("name", "名称"),
                    ("sector_name", "板块/概念"),
                    ("sector_type", "类型"),
                    ("source", "来源"),
                ),
            ),
            "</section>",
        ]
    )


def _html_data_gaps_section(value: Any) -> str:
    gaps = value if isinstance(value, list) else []
    if not gaps:
        return "<section><h2>数据缺口</h2><p>无。</p></section>"
    return "\n".join(
        [
            "<section>",
            "<h2>数据缺口</h2>",
            _rows_table(
                gaps,
                (
                    ("scope", "范围"),
                    ("requested", "请求"),
                    ("actual", "实际"),
                    ("missing", "缺失"),
                    ("reason", "说明"),
                ),
            ),
            "</section>",
        ]
    )


def _rows_table(rows: list[dict[str, Any]], columns: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return '<p class="empty">没有返回可展示数据。</p>'
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{_html_text(_cell_value(row.get(field)))}</td>"
            for field, _ in columns
        )
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _cell_value(value: Any) -> Any:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _status_label(status: str) -> str:
    return {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "missing": "无数据",
        "blocked": "阻塞",
    }.get(status, status)


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1120px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #2563eb; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #e6ebf1; padding: 8px; text-align: left; vertical-align: top; }
th { color: #475569; background: #f8fafc; }
.empty { color: #8a94a6; }
""".strip()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
