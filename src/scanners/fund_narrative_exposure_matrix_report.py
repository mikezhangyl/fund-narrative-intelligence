from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from itertools import combinations
from math import sqrt
from typing import Any

from src.scanners.fund_exposure_comparison_report import (
    FundExposureComparisonConfig,
    execute_fund_exposure_comparison_report,
)
from src.scanners.report_source_disclosure import (
    source_fallback_zh,
    source_status_zh,
    source_warning_summary_zh,
)


@dataclass(frozen=True)
class FundNarrativeExposureMatrixConfig:
    fund_codes: tuple[str, ...]
    sector_trade_date: str | None = None
    limit: int = 10
    sector_types: tuple[str, ...] = ("concept",)
    limit_per_symbol: int = 50
    sector_universe_limit: int | None = None
    exposure_floor: float = 0.0
    high_similarity_threshold: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_fund_narrative_exposure_matrix_report(
    *,
    data_source: Any,
    config: FundNarrativeExposureMatrixConfig,
    narrative_registry: dict[str, Any],
    stock_narrative_mappings: list[dict[str, Any]],
    narrative_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    comparison = execute_fund_exposure_comparison_report(
        data_source=data_source,
        config=FundExposureComparisonConfig(
            fund_codes=config.fund_codes,
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
    fund_reports = _list(comparison.get("fund_reports"))
    fund_rows = _fund_rows(fund_reports, exposure_floor=config.exposure_floor)
    narrative_columns = _narrative_columns(fund_rows)
    similarity_pairs = _similarity_pairs(fund_rows, narrative_columns)
    high_pairs = [
        pair
        for pair in similarity_pairs
        if _float(pair.get("cosine_similarity")) >= config.high_similarity_threshold
    ]
    differentiating = _differentiating_narratives(fund_rows, narrative_columns)
    data_gaps = _data_gaps(fund_reports)
    return {
        "version": "fund-narrative-exposure-matrix-v1",
        "generated_at": _utc_now(),
        "status": str(comparison.get("status") or "missing"),
        "config": {**config.to_dict(), "fund_codes": [row["fund_code"] for row in fund_rows]},
        "summary": {
            "fund_count": len(fund_rows),
            "narrative_count": len(narrative_columns),
            "high_homogeneity_pair_count": len(high_pairs),
            "differentiating_narrative_count": len(differentiating),
            "data_gap_count": len(data_gaps),
            "narrative_source": _narrative_source(comparison),
        },
        "narrative_source": _mapping(comparison.get("narrative_source")),
        "market_data_source": _mapping(comparison.get("market_data_source")),
        "narrative_columns": narrative_columns,
        "fund_rows": fund_rows,
        "narrative_coverage_rows": _narrative_coverage_rows(fund_rows, narrative_columns),
        "similarity_pairs": similarity_pairs,
        "high_homogeneity_pairs": high_pairs,
        "differentiating_narratives": differentiating,
        "data_gaps": data_gaps,
        "source_comparison_report": comparison,
        "degradation_events": list(getattr(data_source, "degradation_events", [])),
        "disclaimer": (
            "Can-Do fund narrative exposure matrix for observability only; not "
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
            "<title>基金组合叙事暴露矩阵</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>基金组合叙事暴露矩阵</h1>",
            '<section class="summary">',
            _html_kv("报告状态", _status_label(str(report.get("status", "")))),
            _html_kv("生成时间", report.get("generated_at", "")),
            _html_narrative_source_notice(report.get("narrative_source")),
            _html_market_data_source_notice(report.get("market_data_source")),
            "<p>本报告用于观察一组基金的叙事暴露重合、同质化与差异化，不构成投资建议、交易策略或涨跌预测。</p>",
            "</section>",
            "<section>",
            "<h2>组合概览</h2>",
            '<div class="metrics">',
            _html_metric("基金数", summary.get("fund_count", 0)),
            _html_metric("叙事数", summary.get("narrative_count", 0)),
            _html_metric("同质化基金对", summary.get("high_homogeneity_pair_count", 0)),
            _html_metric("差异化叙事", summary.get("differentiating_narrative_count", 0)),
            _html_metric("数据缺口", summary.get("data_gap_count", 0)),
            "</div>",
            "</section>",
            _matrix_section(report),
            _rows_section(
                "同质化基金对",
                report.get("high_homogeneity_pairs"),
                (
                    ("fund_a", "基金 A"),
                    ("fund_b", "基金 B"),
                    ("cosine_similarity", "相似度"),
                    ("shared_top_narratives", "共同主叙事"),
                ),
            ),
            _rows_section(
                "差异化叙事",
                report.get("differentiating_narratives"),
                (
                    ("narrative_name", "叙事"),
                    ("dominant_fund", "主导基金"),
                    ("raw_exposure_gap", "暴露差"),
                    ("covered_fund_count", "覆盖基金数"),
                ),
            ),
            _rows_section(
                "叙事覆盖",
                report.get("narrative_coverage_rows"),
                (
                    ("narrative_name", "叙事"),
                    ("covered_fund_count", "覆盖基金数"),
                    ("covered_funds", "覆盖基金"),
                    ("total_raw_exposure", "总暴露"),
                ),
            ),
            _rows_section(
                "数据缺口",
                report.get("data_gaps"),
                (
                    ("fund_code", "基金"),
                    ("gap_type", "缺口类型"),
                    ("message", "说明"),
                ),
            ),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _fund_rows(
    fund_reports: list[dict[str, Any]],
    *,
    exposure_floor: float,
) -> list[dict[str, Any]]:
    rows = []
    for report in fund_reports:
        fund = _mapping(report.get("fund"))
        exposures = {
            str(item.get("narrative_id")): _rounded(_float(item.get("raw_exposure")))
            for item in _list(report.get("narrative_exposures"))
            if str(item.get("narrative_id") or "") and _float(item.get("raw_exposure")) > exposure_floor
        }
        top_narratives = _top_narratives(report)
        rows.append(
            {
                "fund_code": str(fund.get("fund_code") or ""),
                "fund_name": str(fund.get("fund_name") or ""),
                "status": str(report.get("status") or ""),
                "holding_count": len(_list(report.get("holdings"))),
                "top_narratives": top_narratives,
                "narrative_exposures": exposures,
                "data_gap_count": len(_list(report.get("data_gaps"))),
            }
        )
    return rows


def _narrative_columns(fund_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names: dict[str, str] = {}
    totals: dict[str, float] = {}
    coverage: dict[str, int] = {}
    for row in fund_rows:
        top_names = {
            item["narrative_id"]: item["narrative_name"]
            for item in _list(row.get("top_narratives"))
            if item.get("narrative_id")
        }
        for narrative_id, exposure in _mapping(row.get("narrative_exposures")).items():
            names.setdefault(narrative_id, top_names.get(narrative_id, narrative_id))
            totals[narrative_id] = totals.get(narrative_id, 0.0) + _float(exposure)
            if _float(exposure) > 0:
                coverage[narrative_id] = coverage.get(narrative_id, 0) + 1
    return sorted(
        [
            {
                "narrative_id": narrative_id,
                "narrative_name": names.get(narrative_id, narrative_id),
                "total_raw_exposure": _rounded(total),
                "covered_fund_count": coverage.get(narrative_id, 0),
            }
            for narrative_id, total in totals.items()
        ],
        key=lambda item: (-_float(item.get("total_raw_exposure")), str(item.get("narrative_name"))),
    )


def _narrative_coverage_rows(
    fund_rows: list[dict[str, Any]],
    narrative_columns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for column in narrative_columns:
        narrative_id = str(column.get("narrative_id") or "")
        covered = [
            row["fund_code"]
            for row in fund_rows
            if _float(_mapping(row.get("narrative_exposures")).get(narrative_id)) > 0
        ]
        rows.append({**column, "covered_funds": covered})
    return rows


def _similarity_pairs(
    fund_rows: list[dict[str, Any]],
    narrative_columns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    narrative_ids = [str(item.get("narrative_id") or "") for item in narrative_columns]
    pairs = []
    for left, right in combinations(fund_rows, 2):
        left_vector = _vector(left, narrative_ids)
        right_vector = _vector(right, narrative_ids)
        similarity = _cosine_similarity(left_vector, right_vector)
        pairs.append(
            {
                "fund_a": left["fund_code"],
                "fund_b": right["fund_code"],
                "cosine_similarity": _rounded(similarity),
                "shared_top_narratives": _shared_top_narratives(left, right),
            }
        )
    return sorted(
        pairs,
        key=lambda item: (
            -_float(item.get("cosine_similarity")),
            str(item.get("fund_a")),
            str(item.get("fund_b")),
        ),
    )


def _differentiating_narratives(
    fund_rows: list[dict[str, Any]],
    narrative_columns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for column in narrative_columns:
        narrative_id = str(column.get("narrative_id") or "")
        values = {
            row["fund_code"]: _rounded(_float(_mapping(row.get("narrative_exposures")).get(narrative_id)))
            for row in fund_rows
        }
        if not values:
            continue
        dominant_fund = max(values, key=lambda fund_code: values[fund_code])
        gap = _rounded(max(values.values()) - min(values.values()))
        if gap <= 0:
            continue
        rows.append(
            {
                "narrative_id": narrative_id,
                "narrative_name": column.get("narrative_name"),
                "dominant_fund": dominant_fund,
                "raw_exposure_gap": gap,
                "covered_fund_count": column.get("covered_fund_count"),
                "fund_exposures": values,
            }
        )
    return sorted(
        rows,
        key=lambda item: (-_float(item.get("raw_exposure_gap")), str(item.get("narrative_name"))),
    )


def _data_gaps(fund_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in fund_reports:
        fund = _mapping(report.get("fund"))
        fund_code = str(fund.get("fund_code") or "")
        for gap in _list(report.get("data_gaps")):
            rows.append(
                {
                    "fund_code": fund_code,
                    "gap_type": str(gap.get("gap_type") or gap.get("type") or "unknown"),
                    "message": str(gap.get("message") or gap.get("reason") or ""),
                }
            )
    return rows


def _narrative_source(comparison: dict[str, Any]) -> str:
    source = _mapping(comparison.get("narrative_source"))
    return str(source.get("source") or "unspecified")


def _top_narratives(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "narrative_id": str(item.get("narrative_id") or ""),
            "narrative_name": str(item.get("narrative_name") or ""),
            "raw_exposure": _rounded(_float(item.get("raw_exposure"))),
        }
        for item in _list(report.get("narrative_exposures"))
    ][:3]


def _vector(row: dict[str, Any], narrative_ids: list[str]) -> list[float]:
    exposures = _mapping(row.get("narrative_exposures"))
    return [_float(exposures.get(narrative_id)) for narrative_id in narrative_ids]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _shared_top_narratives(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    left_names = {str(item.get("narrative_name") or "") for item in _list(left.get("top_narratives"))}
    right_names = {str(item.get("narrative_name") or "") for item in _list(right.get("top_narratives"))}
    return sorted(name for name in left_names & right_names if name)


def _matrix_section(report: dict[str, Any]) -> str:
    columns = _list(report.get("narrative_columns"))
    rows = _list(report.get("fund_rows"))
    if not columns or not rows:
        return '<section><h2>暴露矩阵</h2><p class="empty">没有返回可展示数据。</p></section>'
    header = "<th>基金</th>" + "".join(
        f"<th>{_html_text(column.get('narrative_name'))}</th>" for column in columns
    )
    body = []
    for row in rows:
        exposures = _mapping(row.get("narrative_exposures"))
        cells = [f"<td>{_html_text(row.get('fund_code'))} {_html_text(row.get('fund_name'))}</td>"]
        cells.extend(
            f"<td>{_html_text(_rounded(_float(exposures.get(str(column.get('narrative_id') or '')))))}</td>"
            for column in columns
        )
        body.append(f"<tr>{''.join(cells)}</tr>")
    table = f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"
    return f"<section><h2>暴露矩阵</h2>{table}</section>"


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
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_rounded(_float(item))}" for key, item in sorted(value.items()))
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
