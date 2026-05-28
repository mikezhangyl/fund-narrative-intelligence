from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from itertools import combinations
from typing import Any

from src.scanners.fund_holding_exposure_report import (
    FundHoldingExposureConfig,
    execute_fund_holding_exposure_report,
)
from src.scanners.report_source_disclosure import (
    aggregate_market_data_sources,
    source_fallback_zh,
    source_status_zh,
    source_warning_summary_zh,
)


@dataclass(frozen=True)
class FundExposureComparisonConfig:
    fund_codes: tuple[str, ...]
    sector_trade_date: str | None = None
    limit: int = 10
    sector_types: tuple[str, ...] = ("concept",)
    limit_per_symbol: int = 50
    sector_universe_limit: int | None = None
    common_min_raw_exposure: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_fund_exposure_comparison_report(
    *,
    data_source: Any,
    config: FundExposureComparisonConfig,
    narrative_registry: dict[str, Any],
    stock_narrative_mappings: list[dict[str, Any]],
    narrative_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fund_codes = _unique_fund_codes(config.fund_codes)
    fund_reports = [
        execute_fund_holding_exposure_report(
            data_source=data_source,
            config=FundHoldingExposureConfig(
                fund_code=fund_code,
                sector_trade_date=config.sector_trade_date,
                limit=config.limit,
                sector_types=config.sector_types,
                limit_per_symbol=config.limit_per_symbol,
                sector_universe_limit=config.sector_universe_limit,
            ),
            narrative_registry=narrative_registry,
            stock_narrative_mappings=stock_narrative_mappings,
            narrative_source=narrative_source,
        )
        for fund_code in fund_codes
    ]
    funds = [_fund_summary(report) for report in fund_reports]
    overlap_pairs = _holding_overlap_pairs(fund_reports)
    common_narratives = _common_narrative_exposures(
        fund_reports,
        min_raw_exposure=config.common_min_raw_exposure,
    )
    differentiating_narratives = _differentiating_narrative_exposures(fund_reports)
    status = _status(fund_reports)
    market_data_source = aggregate_market_data_sources(
        [_mapping(report.get("market_data_source")) for report in fund_reports]
    )
    return {
        "version": "fund-exposure-comparison-v1",
        "generated_at": _utc_now(),
        "status": status,
        "config": {**config.to_dict(), "fund_codes": fund_codes},
        "summary": {
            "fund_count": len(funds),
            "completed_fund_count": sum(1 for report in fund_reports if report["status"] == "completed"),
            "partial_fund_count": sum(1 for report in fund_reports if report["status"] == "partial"),
            "failed_fund_count": sum(1 for report in fund_reports if report["status"] == "failed"),
            "holding_overlap_pair_count": len(overlap_pairs),
            "common_narrative_count": len(common_narratives),
            "differentiating_narrative_count": len(differentiating_narratives),
            "narrative_source": _narrative_source(fund_reports),
        },
        "narrative_source": _first_narrative_source(fund_reports),
        "market_data_source": market_data_source,
        "funds": funds,
        "holding_overlap_pairs": overlap_pairs,
        "common_narrative_exposures": common_narratives,
        "differentiating_narrative_exposures": differentiating_narratives,
        "fund_reports": fund_reports,
        "degradation_events": list(getattr(data_source, "degradation_events", [])),
        "disclaimer": (
            "Can-Do fund exposure comparison report for observability only; not "
            "an investment recommendation, trading strategy, or prediction."
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
            "<title>基金暴露横向比较报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>基金暴露横向比较报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", _status_label(str(report.get("status", "")))),
            _html_kv("生成时间", report.get("generated_at", "")),
            _html_narrative_source_notice(report.get("narrative_source")),
            _html_market_data_source_notice(report.get("market_data_source")),
            "<p>本报告用于横向观察基金持仓、行业与叙事暴露差异，不构成投资建议、交易策略或涨跌预测。</p>",
            "</section>",
            "<section>",
            "<h2>覆盖概览</h2>",
            '<div class="metrics">',
            _html_metric("基金数", summary.get("fund_count", 0)),
            _html_metric("部分完成", summary.get("partial_fund_count", 0)),
            _html_metric("持仓重合组合", summary.get("holding_overlap_pair_count", 0)),
            _html_metric("差异叙事", summary.get("differentiating_narrative_count", 0)),
            "</div>",
            "</section>",
            _rows_section(
                "基金概览",
                report.get("funds"),
                (
                    ("fund_code", "代码"),
                    ("fund_name", "基金名称"),
                    ("status", "状态"),
                    ("holding_count", "持仓数"),
                    ("top3_weight", "前三集中度"),
                    ("top_narrative", "第一叙事"),
                    ("top_industry", "第一行业"),
                ),
            ),
            _rows_section(
                "持仓重合",
                report.get("holding_overlap_pairs"),
                (
                    ("fund_a", "基金 A"),
                    ("fund_b", "基金 B"),
                    ("shared_holding_count", "重合数"),
                    ("shared_names", "重合股票"),
                    ("overlap_weight_fund_a", "A 权重"),
                    ("overlap_weight_fund_b", "B 权重"),
                ),
            ),
            _rows_section(
                "共同叙事",
                report.get("common_narrative_exposures"),
                (
                    ("narrative_name", "叙事"),
                    ("fund_count", "覆盖基金数"),
                    ("min_raw_exposure", "最低暴露"),
                    ("max_raw_exposure", "最高暴露"),
                    ("fund_exposures", "各基金暴露"),
                ),
            ),
            _rows_section(
                "差异叙事",
                report.get("differentiating_narrative_exposures"),
                (
                    ("narrative_name", "叙事"),
                    ("dominant_fund", "主导基金"),
                    ("raw_exposure_gap", "暴露差"),
                    ("fund_exposures", "各基金暴露"),
                ),
            ),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _fund_summary(report: dict[str, Any]) -> dict[str, Any]:
    fund = _mapping(report.get("fund"))
    holdings = _list(report.get("holdings"))
    top_narrative = _first(_list(report.get("narrative_exposures")))
    top_industry = _first(_list(report.get("industry_exposures")))
    concentration = _concentration(holdings)
    return {
        "fund_code": str(fund.get("fund_code") or ""),
        "fund_name": str(fund.get("fund_name") or ""),
        "status": str(report.get("status") or ""),
        "holding_count": len(holdings),
        "holding_weight_sum": _rounded(sum(_float(item.get("weight")) for item in holdings)),
        "concentration": concentration,
        "top_holding_weight": concentration["top_holding_weight"],
        "top3_weight": concentration["top3_weight"],
        "top10_weight": concentration["top10_weight"],
        "top_industry": str(top_industry.get("industry") or ""),
        "top_narrative": str(top_narrative.get("narrative_name") or ""),
        "top_narrative_raw_exposure": _float(top_narrative.get("raw_exposure")),
        "data_gap_count": len(_list(report.get("data_gaps"))),
    }


def _first_narrative_source(fund_reports: list[dict[str, Any]]) -> dict[str, Any]:
    for report in fund_reports:
        source = report.get("narrative_source")
        if isinstance(source, dict):
            return dict(source)
    return {"source": "unspecified"}


def _narrative_source(fund_reports: list[dict[str, Any]]) -> str:
    return str(_first_narrative_source(fund_reports).get("source") or "unspecified")


def _concentration(holdings: list[dict[str, Any]]) -> dict[str, float]:
    weights = sorted((_float(item.get("weight")) for item in holdings), reverse=True)
    return {
        "top_holding_weight": _rounded(sum(weights[:1])),
        "top3_weight": _rounded(sum(weights[:3])),
        "top10_weight": _rounded(sum(weights[:10])),
    }


def _holding_overlap_pairs(fund_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = []
    for left, right in combinations(fund_reports, 2):
        left_fund = _mapping(left.get("fund"))
        right_fund = _mapping(right.get("fund"))
        left_holdings = _holdings_by_symbol(left)
        right_holdings = _holdings_by_symbol(right)
        shared_symbols = sorted(set(left_holdings) & set(right_holdings))
        if not shared_symbols:
            continue
        pairs.append(
            {
                "fund_a": str(left_fund.get("fund_code") or ""),
                "fund_b": str(right_fund.get("fund_code") or ""),
                "shared_holding_count": len(shared_symbols),
                "shared_symbols": shared_symbols,
                "shared_names": [
                    str(left_holdings[symbol].get("stock_name") or right_holdings[symbol].get("stock_name") or "")
                    for symbol in shared_symbols
                ],
                "overlap_weight_fund_a": _rounded(
                    sum(_float(left_holdings[symbol].get("weight")) for symbol in shared_symbols)
                ),
                "overlap_weight_fund_b": _rounded(
                    sum(_float(right_holdings[symbol].get("weight")) for symbol in shared_symbols)
                ),
            }
        )
    return sorted(
        pairs,
        key=lambda item: (
            -int(item["shared_holding_count"]),
            -_float(item["overlap_weight_fund_a"]),
            -_float(item["overlap_weight_fund_b"]),
            str(item["fund_a"]),
            str(item["fund_b"]),
        ),
    )


def _common_narrative_exposures(
    fund_reports: list[dict[str, Any]],
    *,
    min_raw_exposure: float,
) -> list[dict[str, Any]]:
    if not fund_reports:
        return []
    exposures = _narrative_exposure_matrix(fund_reports)
    rows = []
    for narrative_id, payload in exposures.items():
        fund_exposures = payload["fund_exposures"]
        if len(fund_exposures) != len(fund_reports):
            continue
        values = list(fund_exposures.values())
        if min(values) < min_raw_exposure:
            continue
        rows.append(
            {
                "narrative_id": narrative_id,
                "narrative_name": payload["narrative_name"],
                "fund_count": len(fund_exposures),
                "min_raw_exposure": _rounded(min(values)),
                "max_raw_exposure": _rounded(max(values)),
                "fund_exposures": _format_fund_exposures(fund_exposures),
            }
        )
    return sorted(rows, key=lambda item: (-float(item["min_raw_exposure"]), str(item["narrative_name"])))


def _differentiating_narrative_exposures(
    fund_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fund_codes = [str(_mapping(report.get("fund")).get("fund_code") or "") for report in fund_reports]
    exposures = _narrative_exposure_matrix(fund_reports)
    rows = []
    for narrative_id, payload in exposures.items():
        fund_exposures = {
            fund_code: _rounded(float(payload["fund_exposures"].get(fund_code, 0.0)))
            for fund_code in fund_codes
        }
        values = list(fund_exposures.values())
        if not values:
            continue
        dominant_fund = max(fund_exposures, key=lambda fund_code: fund_exposures[fund_code])
        gap = _rounded(max(values) - min(values))
        rows.append(
            {
                "narrative_id": narrative_id,
                "narrative_name": payload["narrative_name"],
                "dominant_fund": dominant_fund,
                "raw_exposure_gap": gap,
                "fund_exposures": _format_fund_exposures(fund_exposures),
            }
        )
    return sorted(rows, key=lambda item: (-float(item["raw_exposure_gap"]), str(item["narrative_name"])))


def _narrative_exposure_matrix(
    fund_reports: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {}
    for report in fund_reports:
        fund_code = str(_mapping(report.get("fund")).get("fund_code") or "")
        for exposure in _list(report.get("narrative_exposures")):
            narrative_id = str(exposure.get("narrative_id") or "")
            if not narrative_id:
                continue
            current = matrix.setdefault(
                narrative_id,
                {
                    "narrative_name": str(exposure.get("narrative_name") or narrative_id),
                    "fund_exposures": {},
                },
            )
            current["fund_exposures"][fund_code] = _float(exposure.get("raw_exposure"))
    return matrix


def _format_fund_exposures(fund_exposures: dict[str, float]) -> str:
    return ", ".join(
        f"{fund_code}: {_rounded(value)}"
        for fund_code, value in sorted(fund_exposures.items())
    )


def _holdings_by_symbol(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(holding.get("stock_code") or ""): holding
        for holding in _list(report.get("holdings"))
        if holding.get("stock_code")
    }


def _status(fund_reports: list[dict[str, Any]]) -> str:
    statuses = [str(report.get("status") or "") for report in fund_reports]
    if statuses and all(status == "completed" for status in statuses):
        return "completed"
    if any(status in {"completed", "partial"} for status in statuses):
        return "partial"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "missing"


def _unique_fund_codes(fund_codes: tuple[str, ...]) -> list[str]:
    seen = set()
    ordered = []
    for fund_code in fund_codes:
        normalized = str(fund_code).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _rows_section(
    title: str,
    value: Any,
    columns: tuple[tuple[str, str], ...],
) -> str:
    rows = _list(value)
    return "\n".join(
        [
            "<section>",
            f"<h2>{_html_text(title)}</h2>",
            _rows_table(rows, columns),
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


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _html_narrative_source_notice(value: Any) -> str:
    return _html_source_notice("叙事数据来源", value)


def _html_market_data_source_notice(value: Any) -> str:
    return _html_source_notice("市场数据来源", value)


def _html_source_notice(title: str, value: Any) -> str:
    source = _mapping(value)
    return "\n".join(
        [
            '<div class="source-notice">',
            f"<h2>{_html_text(title)}</h2>",
            _html_kv("来源", source.get("source", "unspecified")),
            _html_kv("Provider", source.get("provider", "")),
            _html_kv("告警数", source.get("warning_count", 0)),
            _html_kv("降级状态", source_status_zh(source)),
            _html_kv("回退来源", source_fallback_zh(source)),
            _html_kv("告警说明", source_warning_summary_zh(source)),
            "</div>",
        ]
    )


def _status_label(status: str) -> str:
    return {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "missing": "无数据",
    }.get(status, status)


def _first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[0] if rows else {}


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


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #2563eb; }
.source-notice { border: 1px solid #cbd5e1; background: #f8fafc; padding: 10px; margin: 10px 0; }
.source-notice h2 { font-size: 16px; margin: 0 0 8px; }
.source-notice p { margin: 4px 0; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
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
