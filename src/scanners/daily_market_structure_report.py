from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.breadth_scanner import BreadthScanPlanner, execute_breadth_scan
from src.scanners.structure_mapping_report import (
    StructureMappingReportConfig,
    execute_structure_mapping_report,
)


@dataclass(frozen=True)
class DailyMarketStructureReportConfig:
    trade_date: str
    breadth_symbols: tuple[str, ...] | None = None
    breadth_lookback_trading_days: int = 60
    exchange: str = "SSE"
    sector_limit: int = 20
    etf_limit: int = 20
    news_source_provider: str = "tushare"
    news_src: str = "sina"
    news_start_datetime: str | None = None
    news_end_datetime: str | None = None
    news_limit: int = 20
    flow_event_limit: int = 10
    cost_basis_symbols: tuple[str, ...] | None = None
    cost_basis_symbol_limit: int = 3
    benchmark_index_symbols: tuple[str, ...] = ("000300.SH", "000001.SH")
    benchmark_etf_symbols: tuple[str, ...] = ("510300.SH",)
    benchmark_start_date: str | None = None
    structure_sector_name: str = "机器人"
    structure_index_symbol: str = "000300.SH"
    structure_etf_market: str = "cn"
    structure_limit: int = 10
    structure_event_start_date: str | None = None
    structure_event_end_date: str | None = None
    include_turnover: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_daily_market_structure_report(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    sector_heat = _sector_heat(data_source=data_source, config=config)
    etf_heat = _etf_heat(data_source=data_source, config=config)
    structure_mapping = _structure_mapping(data_source=data_source, config=config)
    flow_event_context = _with_flow_cross_links(
        flow_event_context=_flow_event_context(data_source=data_source, config=config),
        sector_heat=sector_heat,
        etf_heat=etf_heat,
        structure_mapping=structure_mapping,
    )
    cost_basis_context = _cost_basis_context(data_source=data_source, config=config)
    benchmark_context = _benchmark_context(data_source=data_source, config=config)
    components = {
        "market_breadth": _market_breadth(data_source=data_source, config=config),
        "benchmark_context": benchmark_context,
        "sector_heat": sector_heat,
        "etf_heat": etf_heat,
        "limit_temperature": _limit_temperature(data_source=data_source, config=config),
        "flow_event_context": flow_event_context,
        "cost_basis_context": cost_basis_context,
        "news_summary": _news_summary(data_source=data_source, config=config),
        "structure_mapping": structure_mapping,
    }
    data_footprint = _data_footprint(components)
    data_gaps = _data_gaps(components=components, config=config)
    return {
        "version": "daily-market-structure-v1",
        "generated_at": _utc_now(),
        "trade_date": config.trade_date,
        "status": _overall_status(components),
        "config": config.to_dict(),
        "data_footprint": data_footprint,
        "data_gaps": data_gaps,
        "data_gap_summary": {
            "gap_count": len(data_gaps),
            "scopes": [gap["scope"] for gap in data_gaps],
        },
        "summary": _summary(components),
        "components": components,
        "degradation_events": list(getattr(data_source, "degradation_events", [])),
        "disclaimer": (
            "Can-Do market structure report for observability only; not an "
            "investment recommendation, trading strategy, or prediction."
        ),
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    components = report.get("components") if isinstance(report.get("components"), dict) else {}
    breadth = _component(components, "market_breadth")
    benchmark = _component(components, "benchmark_context")
    sectors = _component(components, "sector_heat")
    etfs = _component(components, "etf_heat")
    limit = _component(components, "limit_temperature")
    flow_event = _component(components, "flow_event_context")
    cost_basis = _component(components, "cost_basis_context")
    news = _component(components, "news_summary")
    structure = _component(components, "structure_mapping")
    lines = [
        "# Daily Market Structure Report",
        "",
        f"- Status: `{report.get('status', '')}`",
        f"- Trade Date: `{report.get('trade_date', '')}`",
        f"- Generated At: `{report.get('generated_at', '')}`",
        f"- Disclaimer: {report.get('disclaimer', '')}",
        "",
        "## Market Breadth",
        "",
        *(_component_lines(breadth)),
    ]
    metrics = breadth.get("metrics") if isinstance(breadth.get("metrics"), dict) else {}
    if metrics:
        lines.extend(
            [
                f"- MA20 Breadth: `{metrics.get('ma20_breadth', 0.0)}`",
                f"- Advance / Decline: `{metrics.get('advance_count', 0)}` / "
                f"`{metrics.get('decline_count', 0)}`",
                f"- New High / Low: `{metrics.get('new_high_count', 0)}` / "
                f"`{metrics.get('new_low_count', 0)}`",
                f"- Data Fetch Mode: `{breadth.get('data_fetch_mode') or ''}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Benchmark Context",
            "",
            *(_component_lines(benchmark)),
            *_top_rows_lines(benchmark, "symbol"),
            "",
            "## Sector Heat",
            "",
            *(_component_lines(sectors)),
            *_top_rows_lines(sectors, "sector_name"),
            "",
            "## ETF Heat",
            "",
            *(_component_lines(etfs)),
            *_top_rows_lines(etfs, "name"),
            "",
            "## Limit Temperature",
            "",
            *(_component_lines(limit)),
            f"- Temperature: `{limit.get('temperature_label', '')}`",
            f"- Limit Up / Down: `{limit.get('limit_up_count', 0)}` / "
            f"`{limit.get('limit_down_count', 0)}`",
            "",
            "## Flow / Event Context",
            "",
            *(_component_lines(flow_event)),
            *_top_rows_lines(flow_event, "name"),
            "",
            "## Cost Basis Context",
            "",
            *(_component_lines(cost_basis)),
            *_top_rows_lines(cost_basis, "symbol"),
            "",
            "## News Summary",
            "",
            *(_component_lines(news)),
            *_headline_lines(news),
            "",
            "## Structure Mapping",
            "",
            *(_component_lines(structure)),
            "",
            "## Failures",
            "",
            *_failure_lines(components),
            "",
        ]
    )
    return "\n".join(lines)


def render_html_report(report: dict[str, Any]) -> str:
    components = report.get("components") if isinstance(report.get("components"), dict) else {}
    footprint = report.get("data_footprint") if isinstance(report.get("data_footprint"), dict) else {}
    breadth = _component(components, "market_breadth")
    benchmark = _component(components, "benchmark_context")
    sectors = _component(components, "sector_heat")
    etfs = _component(components, "etf_heat")
    limit = _component(components, "limit_temperature")
    flow_event = _component(components, "flow_event_context")
    cost_basis = _component(components, "cost_basis_context")
    news = _component(components, "news_summary")
    structure = _component(components, "structure_mapping")
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>每日市场结构报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>每日市场结构报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", _status_label(report.get("status", ""))),
            _html_kv("交易日", report.get("trade_date", "")),
            _html_kv("生成时间", report.get("generated_at", "")),
            "<p>本报告用于观察市场结构，不构成投资建议、交易策略或涨跌预测。</p>",
            "</section>",
            '<section class="note">',
            "<h2>阅读说明</h2>",
            "<p>本报告回答的是“当天市场结构是什么样”，不是“为什么涨”或“明天怎么走”。</p>",
            "<p>新闻区目前只是当日背景信息，尚未建立新闻与板块、ETF、市场宽度之间的因果关系。</p>",
            "</section>",
            "<section>",
            "<h2>数据调用规模</h2>",
            '<div class="metrics">',
            _html_metric("宽度行情行数", footprint.get("breadth_bar_rows", 0)),
            _html_metric("宽度股票数", footprint.get("breadth_symbol_count", 0)),
            _html_metric("基准行数", footprint.get("benchmark_rows", 0)),
            _html_metric("板块行数", footprint.get("sector_rows", 0)),
            _html_metric("ETF 行数", footprint.get("etf_rows", 0)),
            _html_metric("涨跌停行数", footprint.get("limit_rows", 0)),
            _html_metric("资金/事件行数", footprint.get("flow_event_rows", 0)),
            _html_metric("筹码样本行数", footprint.get("cost_basis_rows", 0)),
            _html_metric("原始新闻条数", footprint.get("news_rows", 0)),
            _html_metric("去重后新闻", footprint.get("news_unique_rows", 0)),
            _html_metric("新闻重复条数", footprint.get("news_duplicate_rows", 0)),
            _html_metric("结构映射行数", footprint.get("structure_mapping_rows", 0)),
            _html_metric("合计数据行", footprint.get("total_rows", 0)),
            "</div>",
            "</section>",
            _html_breadth_section(breadth),
            _html_benchmark_section(benchmark),
            _html_ranked_section("Sector Heat", sectors, "sector_name"),
            _html_ranked_section("ETF Heat", etfs, "name"),
            _html_limit_section(limit),
            _html_flow_event_section(flow_event),
            _html_cost_basis_section(cost_basis),
            _html_news_section(news),
            _html_structure_mapping_section(structure),
            _html_data_gaps_section(report.get("data_gaps")),
            _html_failures_section(components),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _market_breadth(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    try:
        plan = BreadthScanPlanner().build_plan(
            data_source=data_source,
            symbols=list(config.breadth_symbols) if config.breadth_symbols else None,
            end_date=config.trade_date,
            lookback_trading_days=config.breadth_lookback_trading_days,
            exchange=config.exchange,
            analysis_capability="market_breadth_ma20",
        )
        base = {
            "capability": "market_breadth_ma20",
            "status": "blocked" if not plan.can_run else "planned",
            "scan_plan": plan.to_dict(),
            "data_fetch_mode": None,
            "row_count": 0,
            "bar_count": 0,
            "metrics": None,
            "failures": _blocker_failures(plan.blockers),
        }
        if not plan.can_run:
            return base
        result = execute_breadth_scan(
            data_source=data_source,
            plan=plan,
            include_turnover=config.include_turnover,
        )
        return {
            **base,
            "status": "completed",
            "data_fetch_mode": result.get("data_fetch_mode"),
            "row_count": result.get("bar_count", 0),
            "bar_count": result.get("bar_count", 0),
            "metrics": result.get("metrics") or {},
            "failures": [],
        }
    except Exception as exc:
        return _failed_component("market_breadth_ma20", exc)


def _benchmark_context(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    start_date = config.benchmark_start_date or config.trade_date
    components = {
        "index_bars": _list_gateway_component(
            capability="index_bars",
            operation=lambda: data_source.fetch_index_bars(
                symbols=list(config.benchmark_index_symbols),
                start_date=start_date,
                end_date=config.trade_date,
            ),
        ),
        "etf_daily": _list_gateway_component(
            capability="etf_daily",
            operation=lambda: data_source.fetch_etf_data(
                symbols=list(config.benchmark_etf_symbols),
                start_date=start_date,
                end_date=config.trade_date,
            ),
        ),
    }
    index_rows = _nested_rows(components, "index_bars")
    etf_rows = _nested_rows(components, "etf_daily")
    return {
        "capability": "benchmark_context",
        "status": _nested_component_status(components),
        "data_fetch_mode": "gateway_or_provider_daily",
        "provider": "mixed",
        "source": "mixed",
        "row_count": len(index_rows) + len(etf_rows),
        "start_date": start_date,
        "end_date": config.trade_date,
        "components": components,
        "index_rows": index_rows,
        "etf_rows": etf_rows,
        "top_rows": [*index_rows[:3], *etf_rows[:3]],
        "failures": _nested_component_failures(components),
    }


def _sector_heat(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    try:
        rows = list(
            data_source.fetch_sector_data(
                trade_date=config.trade_date,
                limit=config.sector_limit,
            )
        )
        ranked = _rank_rows(rows, limit=config.sector_limit)
        return {
            "capability": "sector_concepts",
            "status": "completed" if rows else "missing",
            "data_fetch_mode": "gateway_provider_neutral",
            "provider": _first_value(rows, "provider"),
            "source": _first_value(rows, "source"),
            "row_count": len(rows),
            "top_rows": ranked,
            "failures": [] if rows else [_failure("sector_concepts", "no rows")],
        }
    except Exception as exc:
        return _failed_component("sector_concepts", exc)


def _etf_heat(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    try:
        rows = list(data_source.fetch_etf_spot(limit=config.etf_limit))
        ranked = _rank_rows(rows, limit=config.etf_limit)
        return {
            "capability": "etf_spot",
            "status": "completed" if rows else "missing",
            "data_fetch_mode": "gateway_provider_neutral",
            "provider": _first_value(rows, "provider"),
            "source": _first_value(rows, "source"),
            "row_count": len(rows),
            "top_rows": ranked,
            "failures": [] if rows else [_failure("etf_spot", "no rows")],
        }
    except Exception as exc:
        return _failed_component("etf_spot", exc)


def _limit_temperature(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    try:
        row = dict(data_source.fetch_limit_up_down_stats(trade_date=config.trade_date))
        limit_up_count = _as_int(row.get("limit_up_count"))
        limit_down_count = _as_int(row.get("limit_down_count"))
        return {
            "capability": "limit_up_down_stats",
            "status": "completed" if row else "missing",
            "data_fetch_mode": "gateway_provider_neutral",
            "provider": str(row.get("provider") or ""),
            "source": str(row.get("source") or ""),
            "row_count": 1 if row else 0,
            "row": row,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "temperature_label": _temperature_label(
                limit_up_count=limit_up_count,
                limit_down_count=limit_down_count,
            ),
            "failures": [] if row else [_failure("limit_up_down_stats", "no rows")],
        }
    except Exception as exc:
        return _failed_component("limit_up_down_stats", exc)


def _news_summary(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    try:
        rows = list(
            data_source.fetch_news_briefs(
                source_provider=config.news_source_provider,
                src=config.news_src,
                start_datetime=config.news_start_datetime
                or f"{config.trade_date} 09:00:00",
                end_datetime=config.news_end_datetime or f"{config.trade_date} 15:30:00",
                limit=config.news_limit,
            )
        )
        deduped_rows = _dedupe_news_rows(rows)
        return {
            "capability": "news_briefs",
            "status": "completed" if rows else "missing",
            "data_fetch_mode": "gateway_tushare_news",
            "provider": _first_value(rows, "provider"),
            "source": _first_value(rows, "source"),
            "raw_headline_count": len(rows),
            "headline_count": len(deduped_rows),
            "duplicate_count": len(rows) - len(deduped_rows),
            "rows": rows,
            "deduped_rows": deduped_rows,
            "briefs": [_brief(row) for row in deduped_rows],
            "channel_counts": _channel_counts(rows),
            "deduplication": {
                "algorithm": "normalize_title_exact_match_v1",
                "description": (
                    "按规范化标题精确分组；同标题多频道新闻保留最早一条，"
                    "合并频道并记录重复条数。不做语义相似、事件聚类或因果归因。"
                ),
            },
            "failures": [] if rows else [_failure("news_briefs", "no rows")],
        }
    except Exception as exc:
        status = "permission_required" if "PROVIDER_PERMISSION_REQUIRED" in str(exc) else "failed"
        return {
            **_failed_component("news_briefs", exc),
            "status": status,
            "data_fetch_mode": "gateway_tushare_news",
            "raw_headline_count": 0,
            "headline_count": 0,
            "duplicate_count": 0,
            "rows": [],
            "deduped_rows": [],
            "briefs": [],
            "channel_counts": {},
            "deduplication": {
                "algorithm": "normalize_title_exact_match_v1",
                "description": "未取得新闻，未执行去重。",
            },
        }


def _structure_mapping(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    try:
        report = execute_structure_mapping_report(
            data_source=data_source,
            config=StructureMappingReportConfig(
                trade_date=config.trade_date,
                sector_name=config.structure_sector_name,
                index_symbol=config.structure_index_symbol,
                event_start_date=config.structure_event_start_date or config.trade_date,
                event_end_date=config.structure_event_end_date or config.trade_date,
                etf_market=config.structure_etf_market,
                limit=config.structure_limit,
            ),
        )
        footprint = report.get("data_footprint")
        row_count = _as_int(
            footprint.get("total_rows") if isinstance(footprint, dict) else 0
        )
        return {
            "capability": "structure_mapping_report",
            "status": str(report.get("status") or "failed"),
            "data_fetch_mode": "gateway_provider_neutral",
            "provider": "mixed",
            "source": "mixed",
            "row_count": row_count,
            "components": report.get("components") or {},
            "data_footprint": footprint or {},
            "data_gaps": report.get("data_gaps") or [],
            "failures": _structure_mapping_failures(report),
        }
    except Exception as exc:
        return _failed_component("structure_mapping_report", exc)


def _flow_event_context(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    components = {
        "northbound_capital": _single_gateway_component(
            capability="northbound_capital",
            operation=lambda: data_source.fetch_northbound_capital(
                trade_date=config.trade_date,
            ),
        ),
        "main_capital_flow": _list_gateway_component(
            capability="main_capital_flow",
            operation=lambda: data_source.fetch_main_capital_flow(
                trade_date=config.trade_date,
                limit=config.flow_event_limit,
            ),
        ),
        "etf_flow": _list_gateway_component(
            capability="etf_flow",
            operation=lambda: data_source.fetch_etf_flow(
                trade_date=config.trade_date,
                limit=config.flow_event_limit,
            ),
        ),
        "dragon_tiger_list": _list_gateway_component(
            capability="dragon_tiger_list",
            operation=lambda: data_source.fetch_dragon_tiger(
                trade_date=config.trade_date,
                limit=config.flow_event_limit,
            ),
        ),
    }
    northbound_rows = _nested_rows(components, "northbound_capital")
    main_flow_rows = _nested_rows(components, "main_capital_flow")
    etf_flow_rows = _nested_rows(components, "etf_flow")
    dragon_tiger_rows = _nested_rows(components, "dragon_tiger_list")
    top_main_flow = _top_money_rows(
        main_flow_rows,
        amount_fields=("main_net_inflow", "net_inflow", "net_buy_amount"),
        limit=5,
    )
    top_etf_flow = _top_money_rows(
        etf_flow_rows,
        amount_fields=("net_inflow", "main_net_inflow", "net_buy_amount"),
        limit=5,
    )
    return {
        "capability": "flow_event_context",
        "status": _nested_component_status(components),
        "data_fetch_mode": "gateway_provider_neutral",
        "provider": "mixed",
        "source": "mixed",
        "row_count": sum(_as_int(component.get("row_count")) for component in components.values()),
        "components": components,
        "northbound_row": northbound_rows[0] if northbound_rows else {},
        "northbound_label": _northbound_label(northbound_rows[0] if northbound_rows else {}),
        "top_rows": top_main_flow,
        "top_main_flow": top_main_flow,
        "top_etf_flow": top_etf_flow,
        "dragon_tiger_rows": dragon_tiger_rows[:5],
        "cross_links": [],
        "failures": _nested_component_failures(components),
    }


def _cost_basis_context(
    *,
    data_source: Any,
    config: DailyMarketStructureReportConfig,
) -> dict[str, Any]:
    symbols = _cost_basis_symbols(config)
    if not symbols:
        return {
            **_failed_component("cost_basis_context", RuntimeError("no symbols configured")),
            "status": "blocked",
            "data_fetch_mode": "gateway_provider_neutral",
            "requested_symbols": [],
            "chip_summaries": [],
            "top_rows": [],
            "rows": [],
        }
    try:
        rows = [
            dict(row)
            for row in data_source.fetch_cyq_chips(
                symbols=symbols,
                trade_date=config.trade_date,
            )
        ]
        chip_summaries = [_chip_summary(row) for row in rows]
        return {
            "capability": "cost_basis_context",
            "status": "completed" if rows else "missing",
            "data_fetch_mode": "gateway_provider_neutral",
            "provider": _first_value(rows, "provider"),
            "source": _first_value(rows, "source"),
            "row_count": len(rows),
            "requested_symbols": symbols,
            "rows": rows,
            "chip_summaries": chip_summaries,
            "top_rows": chip_summaries,
            "failures": [] if rows else [_failure("cost_basis_context", "no rows")],
        }
    except Exception as exc:
        return {
            **_failed_component("cost_basis_context", exc),
            "data_fetch_mode": "gateway_provider_neutral",
            "requested_symbols": symbols,
            "chip_summaries": [],
            "top_rows": [],
            "rows": [],
        }


def _cost_basis_symbols(config: DailyMarketStructureReportConfig) -> list[str]:
    raw_symbols = config.cost_basis_symbols or config.breadth_symbols or ()
    symbols = []
    seen = set()
    for symbol in raw_symbols:
        normalized = str(symbol).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        symbols.append(normalized)
    return symbols[: max(0, config.cost_basis_symbol_limit)]


def _chip_summary(row: dict[str, Any]) -> dict[str, Any]:
    distribution_rows = _cost_distribution_rows(row.get("cost_distribution"))
    peak = _max_row(distribution_rows, "percent") if distribution_rows else {}
    return {
        "symbol": str(row.get("symbol") or ""),
        "trade_date": str(row.get("trade_date") or ""),
        "distribution_bucket_count": len(distribution_rows),
        "peak_price": peak.get("price", ""),
        "peak_percent": peak.get("percent", ""),
        "source": str(row.get("source") or ""),
    }


def _cost_distribution_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _with_flow_cross_links(
    *,
    flow_event_context: dict[str, Any],
    sector_heat: dict[str, Any],
    etf_heat: dict[str, Any],
    structure_mapping: dict[str, Any],
) -> dict[str, Any]:
    nested_flow_components = flow_event_context.get("components")
    flow_components = nested_flow_components if isinstance(nested_flow_components, dict) else {}
    nested_structure_components = structure_mapping.get("components")
    structure_components = (
        nested_structure_components if isinstance(nested_structure_components, dict) else {}
    )
    return {
        **flow_event_context,
        "cross_links": _flow_event_cross_link_rows(
            sector_rows=_nested_rows(structure_components, "sector_constituents"),
            sector_heat_rows=_plain_rows(sector_heat, "top_rows"),
            etf_heat_rows=_plain_rows(etf_heat, "top_rows"),
            index_rows=_nested_rows(structure_components, "index_constituents"),
            main_flow_rows=_nested_rows(flow_components, "main_capital_flow"),
            etf_flow_rows=_nested_rows(flow_components, "etf_flow"),
            dragon_tiger_rows=_nested_rows(flow_components, "dragon_tiger_list"),
        ),
    }


def _single_gateway_component(
    *,
    capability: str,
    operation: Any,
) -> dict[str, Any]:
    try:
        row = dict(operation())
        rows = [row] if row else []
        return _gateway_component_payload(capability=capability, rows=rows)
    except Exception as exc:
        return _gateway_component_payload(
            capability=capability,
            rows=[],
            status="failed",
            failures=[_failure(capability, str(exc))],
        )


def _list_gateway_component(
    *,
    capability: str,
    operation: Any,
) -> dict[str, Any]:
    try:
        rows = [dict(row) for row in operation()]
        return _gateway_component_payload(capability=capability, rows=rows)
    except Exception as exc:
        return _gateway_component_payload(
            capability=capability,
            rows=[],
            status="failed",
            failures=[_failure(capability, str(exc))],
        )


def _gateway_component_payload(
    *,
    capability: str,
    rows: list[dict[str, Any]],
    status: str | None = None,
    failures: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "capability": capability,
        "status": status or ("completed" if rows else "missing"),
        "data_fetch_mode": "gateway_provider_neutral",
        "provider": _first_value(rows, "provider"),
        "source": _first_value(rows, "source"),
        "row_count": len(rows),
        "rows": rows,
        "failures": list(failures or []),
    }


def _nested_component_status(components: dict[str, dict[str, Any]]) -> str:
    statuses = [str(component.get("status") or "") for component in components.values()]
    if statuses and all(status == "completed" for status in statuses):
        return "completed"
    if any(status == "completed" for status in statuses):
        return "partial"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "missing"


def _nested_component_failures(
    components: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for name, component in components.items():
        if component.get("status") == "missing":
            failures.append(_failure(name, "no rows"))
            continue
        for failure in component.get("failures") or []:
            if isinstance(failure, dict):
                failures.append(
                    {
                        "capability": str(failure.get("capability") or name),
                        "reason": str(failure.get("reason") or ""),
                    }
                )
    return failures


def _flow_event_cross_link_rows(
    *,
    sector_rows: list[dict[str, Any]],
    sector_heat_rows: list[dict[str, Any]],
    etf_heat_rows: list[dict[str, Any]],
    index_rows: list[dict[str, Any]],
    main_flow_rows: list[dict[str, Any]],
    etf_flow_rows: list[dict[str, Any]],
    dragon_tiger_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    theme_rows = sector_rows or sector_heat_rows
    return [
        {
            "relation": "主题与主力资金交集",
            "samples": _overlap_names(theme_rows, main_flow_rows),
            "use_case": "观察热门主题样本是否也出现在主力资金净流入列表中。",
        },
        {
            "relation": "主题与龙虎榜交集",
            "samples": _overlap_names(theme_rows, dragon_tiger_rows),
            "use_case": "检查主题样本是否存在异常交易或事件驱动交易痕迹。",
        },
        {
            "relation": "指数与主力资金交集",
            "samples": _overlap_names(index_rows, main_flow_rows),
            "use_case": "观察基准指数样本里是否出现资金流关注对象。",
        },
        {
            "relation": "ETF 热度与 ETF 资金流交集",
            "samples": _overlap_names(etf_heat_rows, etf_flow_rows),
            "use_case": "区分 ETF 涨跌热度与资金流样本是否指向同一标的。",
        },
    ]


def _top_money_rows(
    rows: list[dict[str, Any]],
    *,
    amount_fields: tuple[str, ...],
    limit: int,
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: _first_money_value(row, amount_fields),
        reverse=True,
    )[:limit]


def _first_money_value(row: dict[str, Any], fields: tuple[str, ...]) -> float:
    for field in fields:
        value = row.get(field)
        if value not in (None, "", "--"):
            return _as_float(value)
    return 0.0


def _northbound_label(row: dict[str, Any]) -> str:
    net_buy_amount = _as_float(row.get("net_buy_amount"))
    if net_buy_amount > 0:
        return "net_buy"
    if net_buy_amount < 0:
        return "net_sell"
    if row:
        return "flat"
    return "missing"


def _northbound_context_line(row: dict[str, Any]) -> str:
    if not row:
        return "暂无数据"
    label = {
        "net_buy": "净买入",
        "net_sell": "净卖出",
        "flat": "持平",
    }.get(_northbound_label(row), "暂无数据")
    return f"{label} {row.get('net_buy_amount', '')}"


def _money_context_line(rows: list[dict[str, Any]], amount_field: str) -> str:
    if not rows:
        return "暂无样本"
    first = rows[0]
    amount = first.get(amount_field)
    if amount in (None, "") and amount_field == "main_net_inflow":
        amount = first.get("net_inflow")
    if amount in (None, "") and amount_field == "net_inflow":
        amount = first.get("main_net_inflow")
    return f"{_name_symbol(first)} {amount_field} {amount}"


def _cost_basis_context_line(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "暂无样本"
    first = rows[0]
    return (
        f"{first.get('symbol', '')} 分布桶 {first.get('distribution_bucket_count', 0)}，"
        f"峰值 {first.get('peak_price', '')} / {first.get('peak_percent', '')}"
    )


def _summary(components: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(component.get("status") or "") for component in components.values())
    return {
        "component_status_counts": dict(sorted(counts.items())),
        "completed_components": [
            name for name, component in components.items() if component.get("status") == "completed"
        ],
        "problem_components": [
            name for name, component in components.items() if component.get("status") != "completed"
        ],
    }


def _data_footprint(components: dict[str, dict[str, Any]]) -> dict[str, int]:
    breadth = _component(components, "market_breadth")
    plan = breadth.get("scan_plan") if isinstance(breadth.get("scan_plan"), dict) else {}
    raw_symbols = plan.get("symbols")
    breadth_symbols = raw_symbols if isinstance(raw_symbols, (list, tuple)) else []
    breadth_rows = _as_int(breadth.get("bar_count") or breadth.get("row_count"))
    benchmark_rows = _as_int(_component(components, "benchmark_context").get("row_count"))
    sector_rows = _as_int(_component(components, "sector_heat").get("row_count"))
    etf_rows = _as_int(_component(components, "etf_heat").get("row_count"))
    limit_rows = _as_int(_component(components, "limit_temperature").get("row_count"))
    flow_event_rows = _as_int(_component(components, "flow_event_context").get("row_count"))
    cost_basis_rows = _as_int(_component(components, "cost_basis_context").get("row_count"))
    news_rows = _as_int(_component(components, "news_summary").get("headline_count"))
    raw_news_rows = _as_int(_component(components, "news_summary").get("raw_headline_count"))
    structure_mapping_rows = _as_int(
        _component(components, "structure_mapping").get("row_count")
    )
    return {
        "breadth_bar_rows": breadth_rows,
        "breadth_symbol_count": len(breadth_symbols),
        "benchmark_rows": benchmark_rows,
        "sector_rows": sector_rows,
        "etf_rows": etf_rows,
        "limit_rows": limit_rows,
        "flow_event_rows": flow_event_rows,
        "cost_basis_rows": cost_basis_rows,
        "news_rows": raw_news_rows,
        "news_unique_rows": news_rows,
        "news_duplicate_rows": max(0, raw_news_rows - news_rows),
        "structure_mapping_rows": structure_mapping_rows,
        "total_rows": (
            breadth_rows
            + benchmark_rows
            + sector_rows
            + etf_rows
            + limit_rows
            + flow_event_rows
            + cost_basis_rows
            + raw_news_rows
            + structure_mapping_rows
        ),
    }


def _data_gaps(
    *,
    components: dict[str, dict[str, Any]],
    config: DailyMarketStructureReportConfig,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    breadth = _component(components, "market_breadth")
    plan = breadth.get("scan_plan") if isinstance(breadth.get("scan_plan"), dict) else {}
    raw_symbols = plan.get("symbols")
    symbols = raw_symbols if isinstance(raw_symbols, (list, tuple)) else []
    raw_trade_dates = plan.get("trade_dates")
    trade_dates = raw_trade_dates if isinstance(raw_trade_dates, (list, tuple)) else []
    metrics = breadth.get("metrics") if isinstance(breadth.get("metrics"), dict) else {}
    actual_symbol_count = _as_int(metrics.get("symbol_count"))
    if symbols and actual_symbol_count < len(symbols):
        gaps.append(
            _gap(
                scope="market_breadth_symbols",
                requested=len(symbols),
                actual=actual_symbol_count,
                reason="宽度扫描返回的有效股票数少于请求股票数。",
            )
        )
    expected_bar_rows = len(symbols) * len(trade_dates)
    actual_bar_rows = _as_int(breadth.get("bar_count") or breadth.get("row_count"))
    if expected_bar_rows and actual_bar_rows < expected_bar_rows:
        gaps.append(
            _gap(
                scope="market_breadth_bar_rows",
                requested=expected_bar_rows,
                actual=actual_bar_rows,
                reason="宽度行情行数少于 股票数 x 交易日数，可能存在停牌、缺失或网关覆盖不足。",
            )
        )
    benchmark = _component(components, "benchmark_context")
    if benchmark.get("status") != "completed":
        requested = len(config.benchmark_index_symbols) + len(config.benchmark_etf_symbols)
        gaps.append(
            _gap(
                scope="benchmark_rows",
                requested=requested,
                actual=_as_int(benchmark.get("row_count")),
                reason="指数/ETF 基准上下文未完整返回日线样本。",
            )
        )
    for scope, component_name, requested in (
        ("sector_heat_rows", "sector_heat", config.sector_limit),
        ("etf_heat_rows", "etf_heat", config.etf_limit),
    ):
        actual = _as_int(_component(components, component_name).get("row_count"))
        if requested and actual < requested:
            gaps.append(
                _gap(
                    scope=scope,
                    requested=requested,
                    actual=actual,
                    reason="返回行数少于请求 limit。",
                )
            )
    limit_actual = _as_int(_component(components, "limit_temperature").get("row_count"))
    if limit_actual < 1:
        gaps.append(
            _gap(
                scope="limit_temperature_rows",
                requested=1,
                actual=limit_actual,
                reason="涨跌停温度缺少当日统计行。",
            )
        )
    flow_event = _component(components, "flow_event_context")
    if flow_event.get("status") != "completed":
        gaps.append(
            _gap(
                scope="flow_event_rows",
                requested=1 + (config.flow_event_limit * 3),
                actual=_as_int(flow_event.get("row_count")),
                reason="资金/事件上下文没有完整返回北向、主力资金、ETF 资金流和龙虎榜数据。",
            )
        )
    cost_basis = _component(components, "cost_basis_context")
    if cost_basis.get("status") != "completed":
        requested_symbols = cost_basis.get("requested_symbols")
        requested = len(requested_symbols) if isinstance(requested_symbols, list) else 0
        gaps.append(
            _gap(
                scope="cost_basis_rows",
                requested=requested,
                actual=_as_int(cost_basis.get("row_count")),
                reason="筹码分布样本没有完整返回；可能是 gateway 缓存缺失、权限或该日期无筹码数据。",
            )
        )
    raw_news = _as_int(_component(components, "news_summary").get("raw_headline_count"))
    if config.news_limit and raw_news < config.news_limit:
        gaps.append(
            _gap(
                scope="news_raw_rows",
                requested=config.news_limit,
                actual=raw_news,
                reason="新闻返回条数少于请求 limit；可能是权限、时间窗或来源覆盖限制。",
            )
        )
    structure = _component(components, "structure_mapping")
    if structure.get("status") != "completed":
        gaps.append(
            _gap(
                scope="structure_mapping_rows",
                requested=config.structure_limit,
                actual=_as_int(structure.get("row_count")),
                reason="结构映射新增区块未完整返回。",
            )
        )
    return gaps


def _gap(*, scope: str, requested: int, actual: int, reason: str) -> dict[str, Any]:
    return {
        "scope": scope,
        "requested": requested,
        "actual": actual,
        "missing": max(0, requested - actual),
        "reason": reason,
    }


def _overall_status(components: dict[str, dict[str, Any]]) -> str:
    statuses = {str(component.get("status") or "") for component in components.values()}
    if statuses == {"completed"}:
        return "completed"
    if statuses and statuses <= {"failed", "missing", "blocked", "permission_required"}:
        return "failed"
    return "partial"


def _failed_component(capability: str, exc: Exception) -> dict[str, Any]:
    return {
        "capability": capability,
        "status": "failed",
        "data_fetch_mode": "",
        "provider": "",
        "source": "",
        "row_count": 0,
        "failures": [_failure(capability, str(exc))],
    }


def _blocker_failures(blockers: tuple[str, ...]) -> list[dict[str, str]]:
    return [_failure("market_breadth_ma20", blocker) for blocker in blockers]


def _failure(capability: str, reason: str) -> dict[str, str]:
    return {"capability": capability, "reason": reason}


def _structure_mapping_failures(report: dict[str, Any]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    components = report.get("components")
    if isinstance(components, dict):
        for name, component in components.items():
            if not isinstance(component, dict):
                continue
            for failure in component.get("failures") or []:
                if isinstance(failure, dict):
                    failures.append(
                        {
                            "capability": str(
                                failure.get("capability") or name
                            ),
                            "reason": str(failure.get("reason") or ""),
                        }
                    )
    return failures


def _rank_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (_as_float(row.get("pct_change")), _as_float(row.get("amount"))),
        reverse=True,
    )[:limit]


def _brief(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "datetime": str(row.get("datetime") or ""),
        "title": str(row.get("title") or ""),
        "source": str(row.get("source") or ""),
        "channels": ", ".join(_channels(row)),
        "duplicate_count": _as_int(row.get("duplicate_count") or 1),
        "summary": _truncate(str(row.get("content") or ""), limit=120),
    }


def _dedupe_news_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _news_dedupe_key(row)
        if key not in grouped:
            grouped[key] = {
                **row,
                "channels": _channels(row),
                "duplicate_count": 1,
            }
            continue
        existing = grouped[key]
        existing["duplicate_count"] = _as_int(existing.get("duplicate_count")) + 1
        existing["channels"] = sorted({*_channels(existing), *_channels(row)})
    return list(grouped.values())


def _news_dedupe_key(row: dict[str, Any]) -> str:
    title = _normalize_news_text(row.get("title"))
    if title:
        return f"title:{title}"
    content = _normalize_news_text(row.get("content"))
    return f"content:{content[:80]}"


def _normalize_news_text(value: Any) -> str:
    return "".join(str(value or "").split()).lower()


def _channels(row: dict[str, Any]) -> list[str]:
    channels = row.get("channels")
    if isinstance(channels, list):
        return sorted({str(channel).strip() for channel in channels if str(channel).strip()})
    if channels:
        return sorted({part.strip() for part in str(channels).split(",") if part.strip()})
    return []


def _channel_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(_channels(row))
    return dict(sorted(counts.items()))


def _temperature_label(*, limit_up_count: int, limit_down_count: int) -> str:
    if limit_down_count >= 20 or limit_down_count > limit_up_count:
        return "cold"
    if limit_up_count >= 30 and limit_up_count >= max(1, limit_down_count) * 3:
        return "hot"
    if limit_up_count >= 10:
        return "warm"
    return "neutral"


def _component(components: dict[str, Any], name: str) -> dict[str, Any]:
    value = components.get(name)
    return value if isinstance(value, dict) else {}


def _component_lines(component: dict[str, Any]) -> list[str]:
    return [
        f"- Status: `{component.get('status', '')}`",
        f"- Rows: `{component.get('row_count', component.get('headline_count', 0))}`",
        f"- Source: `{component.get('source', '')}`",
    ]


def _top_rows_lines(component: dict[str, Any], label_field: str) -> list[str]:
    rows = component.get("top_rows")
    if not isinstance(rows, list) or not rows:
        return ["- Top Rows: None"]
    lines = ["", "| Name | Change | Source |", "| --- | ---: | --- |"]
    for row in rows[:5]:
        if not isinstance(row, dict):
            continue
        label = str(row.get(label_field) or row.get("symbol") or "")
        change = row.get("pct_change", "")
        source = str(row.get("source") or "")
        lines.append(f"| {label} | {change} | {source} |")
    return lines


def _headline_lines(component: dict[str, Any]) -> list[str]:
    briefs = component.get("briefs")
    if not isinstance(briefs, list) or not briefs:
        return ["- Headlines: None"]
    return [f"- {item.get('datetime', '')}: {item.get('title', '')}" for item in briefs[:5] if isinstance(item, dict)]


def _failure_lines(components: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for name, component in components.items():
        if not isinstance(component, dict):
            continue
        for failure in component.get("failures", []):
            if isinstance(failure, dict):
                lines.append(
                    f"- `{name}` / `{failure.get('capability', '')}`: "
                    f"{failure.get('reason', '')}"
                )
    return lines or ["- None"]


def _html_breadth_section(component: dict[str, Any]) -> str:
    metrics = component.get("metrics") if isinstance(component.get("metrics"), dict) else {}
    plan = component.get("scan_plan") if isinstance(component.get("scan_plan"), dict) else {}
    rows = [
        "<section>",
        "<h2>市场宽度</h2>",
        "<p>市场宽度用于观察上涨是否扩散到更多股票。本报告的 MA20 宽度表示样本股票中收盘价高于 20 日均线的比例。</p>",
        '<div class="metrics">',
        _html_metric("状态", _status_label(component.get("status", ""))),
        _html_metric("行情行数", component.get("row_count", 0)),
        _html_metric("样本股票数", metrics.get("symbol_count", 0)),
        _html_metric("交易窗口", f"{plan.get('start_date', '')} 至 {plan.get('end_date', '')}"),
        _html_metric("数据读取模式", component.get("data_fetch_mode", ""), "来源: gateway breadth-window 或 daily-bars。"),
        _html_metric("MA20 宽度", f"{metrics.get('ma20_breadth', 0.0)}%", "口径: 样本股票中收盘价高于 20 日均线的比例。来源: gateway 宽度窗口行情。"),
        _html_metric("上涨 / 下跌家数", f"{metrics.get('advance_count', 0)} / {metrics.get('decline_count', 0)}", "口径: 最新交易日 close 相对 pre_close 上涨或下跌的样本股票数。"),
        _html_metric("新高 / 新低家数", f"{metrics.get('new_high_count', 0)} / {metrics.get('new_low_count', 0)}", "口径: 当前可用窗口内的新高/新低，不等同完整 52 周新高低。"),
        _html_metric("成交量是否放大", "是" if metrics.get("volume_expansion") else "否"),
        "</div>",
        "</section>",
    ]
    return "\n".join(rows)


def _html_benchmark_section(component: dict[str, Any]) -> str:
    index_rows = _plain_rows(component, "index_rows")
    etf_rows = _plain_rows(component, "etf_rows")
    return "\n".join(
        [
            "<section>",
            "<h2>指数/ETF 基准上下文</h2>",
            "<p>这一段读取已有的指数日线和 ETF 日线，用来给宽度、板块和资金上下文提供基准参照。这里不计算趋势信号，只展示当日样本。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("行数", component.get("row_count", 0)),
            _html_metric(
                "日期窗口",
                f"{component.get('start_date', '')} 至 {component.get('end_date', '')}",
            ),
            _html_metric("指数样本", _sample_names(index_rows, limit=3)),
            _html_metric("ETF 样本", _sample_names(etf_rows, limit=3)),
            "</div>",
            "<h3>指数日线样本</h3>",
            _html_compact_table(
                "指数日线样本",
                index_rows,
                (
                    ("symbol", "代码"),
                    ("trade_date", "日期"),
                    ("close", "收盘"),
                    ("pre_close", "前收"),
                    ("source", "来源"),
                ),
            ),
            "<h3>ETF 日线样本</h3>",
            _html_compact_table(
                "ETF 日线样本",
                etf_rows,
                (
                    ("symbol", "代码"),
                    ("trade_date", "日期"),
                    ("close", "收盘"),
                    ("pre_close", "前收"),
                    ("source", "来源"),
                ),
            ),
            "</section>",
        ]
    )


def _html_ranked_section(title: str, component: dict[str, Any], label_field: str) -> str:
    chinese_title = "板块热度" if title == "Sector Heat" else "ETF 热度"
    name_header = "板块名称" if title == "Sector Heat" else "ETF 名称"
    rows = component.get("top_rows")
    table_rows = []
    if isinstance(rows, list):
        for row in rows[:10]:
            if isinstance(row, dict):
                label = row.get(label_field) or row.get("symbol") or ""
                table_rows.append(
                    "<tr>"
                    f"<td>{_html_text(label)}</td>"
                    f"<td>{_html_text(row.get('pct_change', ''))}</td>"
                    f"<td>{_html_text(row.get('amount', ''))}</td>"
                    f"<td>{_html_text(row.get('source', ''))}</td>"
                    "</tr>"
                )
    if not table_rows:
        table_rows.append('<tr><td colspan="4">No rows</td></tr>')
    return "\n".join(
        [
            "<section>",
            f"<h2>{_html_text(chinese_title)}</h2>",
            "<p>涨跌幅表示对应交易日相对上一交易日收盘价的百分比变化，不代表资金流入比例，也不是预测信号。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("行数", component.get("row_count", 0)),
            _html_metric("数据来源", component.get("source", ""), "hover 仅说明当前行数据源；涨跌幅来自该数据源的行情字段。"),
            "</div>",
            "<table>",
            f"<thead><tr><th>{name_header}</th><th>涨跌幅（%）</th><th>成交额</th><th>数据来源</th></tr></thead>",
            f"<tbody>{''.join(table_rows)}</tbody>",
            "</table>",
            "</section>",
        ]
    )


def _html_limit_section(component: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<section>",
            "<h2>涨跌停温度</h2>",
            "<p>涨跌停温度用于观察短线情绪强弱。涨停多、跌停少通常表示风险偏好较强；跌停增加则提示情绪压力。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("数据来源", component.get("source", ""), "来源: provider-neutral limit-up/down gateway endpoint。"),
            _html_metric("温度标签", _temperature_label_cn(component.get("temperature_label", ""))),
            _html_metric("涨停家数", component.get("limit_up_count", 0)),
            _html_metric("跌停家数", component.get("limit_down_count", 0)),
            "</div>",
            "</section>",
        ]
    )


def _html_flow_event_section(component: dict[str, Any]) -> str:
    nested_components = component.get("components")
    components = nested_components if isinstance(nested_components, dict) else {}
    northbound_rows = _nested_rows(components, "northbound_capital")
    main_flow_rows = _plain_rows(component, "top_main_flow")
    etf_flow_rows = _plain_rows(component, "top_etf_flow")
    dragon_tiger_rows = _plain_rows(component, "dragon_tiger_rows")
    cross_links = _plain_rows(component, "cross_links")
    northbound = northbound_rows[0] if northbound_rows else {}
    return "\n".join(
        [
            "<section>",
            "<h2>资金/事件上下文</h2>",
            "<p>这一段把 gateway 已有的北向资金、主力资金、ETF 资金流和龙虎榜接入日报。它只说明资金与事件样本的方向和重叠，不解释成买卖信号。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("行数", component.get("row_count", 0)),
            _html_metric(
                "北向资金",
                _northbound_context_line(northbound),
                "口径: gateway northbound capital 返回的 net_buy_amount。",
            ),
            _html_metric(
                "主力净流入最高",
                _money_context_line(main_flow_rows, "main_net_inflow"),
            ),
            _html_metric(
                "ETF 净流入最高",
                _money_context_line(etf_flow_rows, "net_inflow"),
            ),
            _html_metric("龙虎榜样本", len(dragon_tiger_rows)),
            "</div>",
            "<h3>资金/事件交叉线索</h3>",
            _html_compact_table(
                "资金/事件交叉关系",
                cross_links,
                (
                    ("relation", "关系"),
                    ("samples", "重叠样本"),
                    ("use_case", "可解释含义"),
                ),
            ),
            "<h3>主力资金样本</h3>",
            _html_compact_table(
                "主力资金净流入",
                main_flow_rows,
                (
                    ("name", "名称"),
                    ("symbol", "代码"),
                    ("main_net_inflow", "主力净流入"),
                    ("pct_change", "涨跌幅"),
                    ("source", "来源"),
                ),
            ),
            "<h3>ETF 资金流样本</h3>",
            _html_compact_table(
                "ETF 资金流",
                etf_flow_rows,
                (
                    ("name", "名称"),
                    ("symbol", "代码"),
                    ("net_inflow", "净流入"),
                    ("pct_change", "涨跌幅"),
                    ("source", "来源"),
                ),
            ),
            "<h3>龙虎榜样本</h3>",
            _html_compact_table(
                "龙虎榜",
                dragon_tiger_rows,
                (
                    ("name", "名称"),
                    ("symbol", "代码"),
                    ("reason", "上榜原因"),
                    ("net_buy_amount", "净买入"),
                    ("source", "来源"),
                ),
            ),
            "</section>",
        ]
    )


def _html_cost_basis_section(component: dict[str, Any]) -> str:
    summaries = _plain_rows(component, "chip_summaries")
    requested_symbols = component.get("requested_symbols")
    symbol_count = len(requested_symbols) if isinstance(requested_symbols, list) else 0
    return "\n".join(
        [
            "<section>",
            "<h2>成本/筹码上下文</h2>",
            "<p>这一段读取 gateway 已有的 CYQ 筹码分布样本，用来观察样本股票的成本分布形状。当前只做确定性摘要，不做支撑位、压力位或买卖判断。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("返回股票数", component.get("row_count", 0)),
            _html_metric("请求股票数", symbol_count),
            _html_metric("样本概览", _cost_basis_context_line(summaries)),
            "</div>",
            "<h3>筹码分布样本</h3>",
            _html_compact_table(
                "筹码分布样本",
                summaries,
                (
                    ("symbol", "代码"),
                    ("trade_date", "日期"),
                    ("distribution_bucket_count", "分布桶数"),
                    ("peak_price", "占比最高价格"),
                    ("peak_percent", "最高占比"),
                    ("source", "来源"),
                ),
            ),
            "</section>",
        ]
    )


def _html_news_section(component: dict[str, Any]) -> str:
    briefs = component.get("briefs")
    items = []
    if isinstance(briefs, list):
        for item in briefs[:10]:
            if isinstance(item, dict):
                duplicate_count = _as_int(item.get("duplicate_count") or 1)
                duplicate_note = f"重复 {duplicate_count} 条；" if duplicate_count > 1 else ""
                items.append(
                    "<li>"
                    f"<strong>{_html_text(item.get('title', ''))}</strong>"
                    f"<span>{_html_text(item.get('datetime', ''))}</span>"
                    f"<small>{_html_text(duplicate_note)}频道: {_html_text(item.get('channels', ''))}</small>"
                    f"<p>{_html_text(item.get('summary', ''))}</p>"
                    "</li>"
                )
    if not items:
        items.append("<li>No headlines</li>")
    return "\n".join(
        [
            "<section>",
            "<h2>当日新闻背景</h2>",
            "<p>以下新闻来自 Tushare news briefs。当前版本只做标题级确定性去重，不做语义聚类、因果解释或板块归因。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("原始新闻", component.get("raw_headline_count", 0), "来源: gateway Tushare news briefs 返回的原始条数。"),
            _html_metric("去重后新闻", component.get("headline_count", 0), "算法: 规范化标题后精确匹配，同标题多频道合并。"),
            _html_metric("重复条数", component.get("duplicate_count", 0), "重复条数 = 原始新闻 - 去重后新闻。"),
            _html_metric("数据来源", component.get("source", ""), "来源: gateway Tushare news briefs。"),
            "</div>",
            f"<ul class=\"news-list\">{''.join(items)}</ul>",
            "</section>",
        ]
    )


def _html_structure_mapping_section(component: dict[str, Any]) -> str:
    nested_components = component.get("components")
    components = nested_components if isinstance(nested_components, dict) else {}
    sector_rows = _nested_rows(components, "sector_constituents")
    etf_rows = _nested_rows(components, "etf_basic")
    index_rows = _nested_rows(components, "index_constituents")
    margin_summary_rows = _nested_rows(components, "margin_summary")
    margin_detail_rows = _nested_rows(components, "margin_detail")
    event_rows = _nested_rows(components, "earnings_calendar")
    margin_leader = _max_row(margin_detail_rows, "financing_balance")
    return "\n".join(
        [
            '<section class="new-update">',
            "<h2>市场结构映射（新增）</h2>",
            "<p>红色区块为本次临时标注的新增内容。这里不再展示任务状态，而是把新增数据转成可读的结构上下文。</p>",
            '<div class="metrics">',
            _html_metric("状态", _status_label(component.get("status", ""))),
            _html_metric("行数", component.get("row_count", 0)),
            _html_metric("数据读取模式", component.get("data_fetch_mode", "")),
            "</div>",
            "<h3>结构解释线索</h3>",
            '<div class="insight-grid">',
            _html_insight(
                "主题成分样本",
                _sector_context_line(sector_rows),
            ),
            _html_insight(
                "ETF 映射样本",
                _sample_names(etf_rows, limit=3),
            ),
            _html_insight(
                "指数权重样本",
                _index_context_line(index_rows),
            ),
            _html_insight(
                "融资余额最高样本",
                _margin_context_line(margin_summary_rows, margin_leader),
            ),
            _html_insight(
                "事件日历样本",
                _event_context_line(event_rows),
            ),
            "</div>",
            "<h3>交叉线索</h3>",
            _html_compact_table(
                "结构交叉关系",
                _cross_link_rows(
                    sector_rows=sector_rows,
                    index_rows=index_rows,
                    margin_rows=margin_detail_rows,
                    event_rows=event_rows,
                ),
                (
                    ("relation", "关系"),
                    ("samples", "重叠样本"),
                    ("use_case", "可解释含义"),
                ),
            ),
            "<h3>可解释用途</h3>",
            "<ul>",
            "<li>把板块热度或新闻主题落到具体成分股，避免只停留在板块名字。</li>",
            "<li>判断 ETF 或指数是否可以作为某类主题、宽基或组合暴露的代理参照。</li>",
            "<li>用融资融券和事件日历补充风险上下文，但不把它们解释成买卖信号。</li>",
            "</ul>",
            "<h3>关键样本</h3>",
            _html_compact_table(
                "板块成分样本",
                sector_rows[:5],
                (
                    ("name", "名称"),
                    ("symbol", "代码"),
                    ("pct_change", "涨跌幅"),
                    ("source", "来源"),
                ),
            ),
            _html_compact_table(
                "融资融券样本",
                sorted(
                    margin_detail_rows,
                    key=lambda row: _as_float(row.get("financing_balance")),
                    reverse=True,
                )[:5],
                (
                    ("name", "名称"),
                    ("symbol", "代码"),
                    ("financing_balance", "融资余额"),
                    ("source", "来源"),
                ),
            ),
            _html_compact_table(
                "事件日历样本",
                event_rows[:5],
                (
                    ("ann_date", "日期"),
                    ("name", "名称"),
                    ("symbol", "代码"),
                    ("event_type", "事件"),
                ),
            ),
            "</section>",
        ]
    )


def _html_insight(label: str, value: str) -> str:
    return (
        '<div class="insight">'
        f"<strong>{_html_text(label)}</strong>"
        f"<p>{_html_text(value or '暂无样本')}</p>"
        "</div>"
    )


def _html_compact_table(
    title: str,
    rows: list[dict[str, Any]],
    columns: tuple[tuple[str, str], ...],
) -> str:
    if not rows:
        return f"<h4>{_html_text(title)}</h4><p>暂无样本。</p>"
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(
                f"<td>{_html_text(row.get(field, ''))}</td>"
                for field, _ in columns
            )
            + "</tr>"
        )
    return "\n".join(
        [
            f"<h4>{_html_text(title)}</h4>",
            "<table>",
            f"<thead><tr>{header}</tr></thead>",
            f"<tbody>{''.join(body)}</tbody>",
            "</table>",
        ]
    )


def _nested_rows(components: dict[str, Any], key: str) -> list[dict[str, Any]]:
    nested = _component(components, key)
    rows = nested.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _plain_rows(component: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = component.get(key)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _sample_names(rows: list[dict[str, Any]], *, limit: int) -> str:
    return "，".join(_name_symbol(row) for row in rows[:limit] if _name_symbol(row))


def _sector_context_line(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    first = rows[0]
    sector_name = str(first.get("sector_name") or "板块")
    samples = _sample_names(rows, limit=3)
    return f"{sector_name} 成分样本：{samples}"


def _index_context_line(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    first = rows[0]
    index_symbol = str(first.get("index_symbol") or "指数")
    weight = first.get("weight", "")
    weight_text = f"，权重 {weight}" if weight not in (None, "") else ""
    return f"{index_symbol} 样本：{_name_symbol(first)}{weight_text}"


def _margin_context_line(
    summary_rows: list[dict[str, Any]],
    margin_leader: dict[str, Any],
) -> str:
    parts = []
    if margin_leader:
        parts.append(
            f"{_name_symbol(margin_leader)} 融资余额 {margin_leader.get('financing_balance', '')}"
        )
    if summary_rows:
        parts.append(f"全市场融资余额 {summary_rows[0].get('financing_balance', '')}")
    return "；".join(part for part in parts if part)


def _event_context_line(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    samples = []
    for row in rows[:3]:
        label = _name_symbol(row)
        event_type = row.get("event_type", "")
        ann_date = row.get("ann_date", "")
        if label:
            samples.append(f"{label}（{ann_date}，{event_type}）")
    return "；".join(samples)


def _cross_link_rows(
    *,
    sector_rows: list[dict[str, Any]],
    index_rows: list[dict[str, Any]],
    margin_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "relation": "主题与指数交集",
            "samples": _overlap_names(sector_rows, index_rows),
            "use_case": "判断热门主题样本是否同时进入基准指数。",
        },
        {
            "relation": "主题与融资融券交集",
            "samples": _overlap_names(sector_rows, margin_rows),
            "use_case": "观察主题样本是否也有杠杆交易关注。",
        },
        {
            "relation": "主题与事件日历交集",
            "samples": _overlap_names(sector_rows, event_rows),
            "use_case": "检查主题样本是否存在公告或事件扰动。",
        },
        {
            "relation": "指数与融资融券交集",
            "samples": _overlap_names(index_rows, margin_rows),
            "use_case": "观察基准样本中的杠杆关注对象。",
        },
    ]


def _overlap_names(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
) -> str:
    right_keys = {
        key
        for row in right_rows
        for key in _row_match_keys(row)
    }
    overlaps: list[str] = []
    seen: set[str] = set()
    for row in left_rows:
        if not (_row_match_keys(row) & right_keys):
            continue
        label = _name_symbol(row)
        if label and label not in seen:
            overlaps.append(label)
            seen.add(label)
    return "，".join(overlaps[:5]) or "暂无重叠"


def _row_match_keys(row: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    symbol = str(row.get("symbol") or "").strip()
    if symbol:
        keys.add(symbol.upper())
        keys.add(symbol.split(".", 1)[0].upper())
    name = str(row.get("name") or "").strip()
    if name:
        keys.add(f"name:{name}")
    return keys


def _max_row(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    if not rows:
        return {}
    return max(rows, key=lambda row: _as_float(row.get(field)))


def _name_symbol(row: dict[str, Any]) -> str:
    name = str(row.get("name") or row.get("sector_name") or "")
    symbol = str(row.get("symbol") or "")
    if name and symbol:
        return f"{name} / {symbol}"
    return name or symbol


def _html_data_gaps_section(raw_gaps: Any) -> str:
    gaps = raw_gaps if isinstance(raw_gaps, list) else []
    rows = []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{_html_text(gap.get('scope', ''))}</td>"
            f"<td>{_html_text(gap.get('requested', 0))}</td>"
            f"<td>{_html_text(gap.get('actual', 0))}</td>"
            f"<td>{_html_text(gap.get('missing', 0))}</td>"
            f"<td>{_html_text(gap.get('reason', ''))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="5">未发现明显数据缺口</td></tr>')
    return "\n".join(
        [
            "<section>",
            "<h2>数据缺口诊断</h2>",
            "<p>这里检查已连通接口是否返回少于请求规模的数据。缺口不一定是错误，可能来自停牌、时间窗、权限或上游覆盖。</p>",
            "<table>",
            "<thead><tr><th>范围</th><th>请求</th><th>实际</th><th>缺口</th><th>说明</th></tr></thead>",
            f"<tbody>{''.join(rows)}</tbody>",
            "</table>",
            "</section>",
        ]
    )


def _html_failures_section(components: dict[str, Any]) -> str:
    failures = _failure_lines(components)
    items = "".join(f"<li>{_html_text(line.removeprefix('- '))}</li>" for line in failures)
    return "\n".join(["<section>", "<h2>失败与缺失</h2>", f"<ul>{items}</ul>", "</section>"])


def _html_metric(label: str, value: Any, title: str = "") -> str:
    title_attr = f' title="{_html_text(title)}"' if title else ""
    return (
        f'<div class="metric"{title_attr}>'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _first_nested_label(component: dict[str, Any]) -> str:
    rows = component.get("rows")
    if not isinstance(rows, list) or not rows:
        return ""
    first = rows[0]
    if not isinstance(first, dict):
        return ""
    return str(
        first.get("name")
        or first.get("sector_name")
        or first.get("symbol")
        or first.get("event_type")
        or ""
    )


def _status_label(value: Any) -> str:
    labels = {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "missing": "无数据",
        "blocked": "阻塞",
        "permission_required": "需要权限",
        "planned": "已计划",
    }
    return labels.get(str(value or ""), str(value or ""))


def _temperature_label_cn(value: Any) -> str:
    labels = {
        "hot": "偏热",
        "warm": "温和",
        "neutral": "中性",
        "cold": "偏冷",
    }
    return labels.get(str(value or ""), str(value or ""))


def _html_text(value: Any) -> str:
    if value is None:
        return ""
    return escape(str(value), quote=True)


def _html_styles() -> str:
    return """
body {
  margin: 0;
  color: #17201b;
  background: #f6f7f3;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}
h1, h2 {
  letter-spacing: 0;
}
h1 {
  margin: 0 0 20px;
  font-size: 34px;
}
h2 {
  margin: 0 0 14px;
  font-size: 21px;
}
section {
  margin-top: 18px;
  padding: 18px;
  border: 1px solid #d7ddd2;
  background: #ffffff;
}
.summary {
  border-left: 4px solid #28666e;
}
.new-update, .new-update * {
  color: #b91c1c;
}
.new-update {
  border-color: #ef4444;
  border-left: 4px solid #b91c1c;
}
.insight-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.insight {
  padding: 10px;
  border: 1px solid #fecaca;
  background: #fff7f7;
}
.insight p {
  margin: 8px 0 0;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.metric {
  padding: 10px;
  background: #eef3f1;
}
.metric span {
  display: block;
  color: #5a675f;
  font-size: 12px;
}
.metric strong {
  display: block;
  margin-top: 5px;
  font-size: 16px;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 14px;
}
th, td {
  padding: 10px;
  border-bottom: 1px solid #e4e8e0;
  text-align: left;
}
th {
  color: #445149;
  background: #f0f3ed;
}
.news-list {
  padding-left: 20px;
}
.news-list li {
  margin: 12px 0;
}
.news-list span {
  display: block;
  color: #5f6c64;
  font-size: 13px;
}
""".strip()


def _first_value(rows: list[dict[str, Any]], field: str) -> str:
    if not rows:
        return ""
    return str(rows[0].get(field) or "")


def _as_float(value: Any) -> float:
    if value in (None, "", "--"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    if value in (None, "", "--"):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _truncate(text: str, *, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
