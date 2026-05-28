from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.scanners.daily_market_structure_report import (  # noqa: E402
    DailyMarketStructureReportConfig,
    execute_daily_market_structure_report,
    render_html_report,
)

DEFAULT_BREADTH_SYMBOLS = ("600519.SH", "000001.SZ", "300750.SZ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Can-Do daily market structure report."
    )
    parser.add_argument("--trade-date", default=date.today().isoformat())
    parser.add_argument(
        "--breadth-symbols",
        help=(
            "Comma-separated Tushare symbols for the breadth sample. Defaults to "
            f"{','.join(DEFAULT_BREADTH_SYMBOLS)}."
        ),
    )
    parser.add_argument(
        "--breadth-symbols-file",
        type=Path,
        help="Optional file containing breadth symbols separated by commas or newlines.",
    )
    parser.add_argument(
        "--use-stock-metadata",
        action="store_true",
        help="Resolve breadth symbols from gateway/provider stock metadata.",
    )
    parser.add_argument("--breadth-lookback-trading-days", type=int, default=60)
    parser.add_argument("--exchange", default="SSE")
    parser.add_argument("--sector-limit", type=int, default=20)
    parser.add_argument("--etf-limit", type=int, default=20)
    parser.add_argument("--news-source-provider", default="tushare")
    parser.add_argument("--news-src", default="sina")
    parser.add_argument("--news-start-datetime")
    parser.add_argument("--news-end-datetime")
    parser.add_argument("--news-limit", type=int, default=20)
    parser.add_argument("--flow-event-limit", type=int, default=10)
    parser.add_argument(
        "--cost-basis-symbols",
        help="Optional comma-separated symbols for CYQ cost-basis samples.",
    )
    parser.add_argument("--cost-basis-symbol-limit", type=int, default=3)
    parser.add_argument("--benchmark-index-symbols", default="000300.SH,000001.SH")
    parser.add_argument("--benchmark-etf-symbols", default="510300.SH")
    parser.add_argument("--benchmark-start-date")
    parser.add_argument("--structure-sector-name", default="机器人")
    parser.add_argument("--structure-index-symbol", default="000300.SH")
    parser.add_argument("--structure-etf-market", default="cn")
    parser.add_argument("--structure-limit", type=int, default=10)
    parser.add_argument("--structure-event-start-date")
    parser.add_argument("--structure-event-end-date")
    parser.add_argument("--no-turnover", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_positive(parser, "breadth-lookback-trading-days", args.breadth_lookback_trading_days)
    _validate_positive(parser, "sector-limit", args.sector_limit)
    _validate_positive(parser, "etf-limit", args.etf_limit)
    _validate_positive(parser, "news-limit", args.news_limit)
    _validate_positive(parser, "flow-event-limit", args.flow_event_limit)
    _validate_positive(parser, "cost-basis-symbol-limit", args.cost_basis_symbol_limit)
    _validate_positive(parser, "structure-limit", args.structure_limit)
    try:
        breadth_symbols = _resolve_symbol_inputs(
            symbols_text=args.breadth_symbols,
            symbols_file=args.breadth_symbols_file,
            use_stock_metadata=args.use_stock_metadata,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = DailyMarketStructureReportConfig(
        trade_date=args.trade_date,
        breadth_symbols=tuple(breadth_symbols) if breadth_symbols is not None else None,
        breadth_lookback_trading_days=args.breadth_lookback_trading_days,
        exchange=args.exchange,
        sector_limit=args.sector_limit,
        etf_limit=args.etf_limit,
        news_source_provider=args.news_source_provider,
        news_src=args.news_src,
        news_start_datetime=args.news_start_datetime
        or f"{args.trade_date} 09:00:00",
        news_end_datetime=args.news_end_datetime or f"{args.trade_date} 15:30:00",
        news_limit=args.news_limit,
        flow_event_limit=args.flow_event_limit,
        cost_basis_symbols=tuple(_parse_symbol_text(args.cost_basis_symbols or ""))
        or None,
        cost_basis_symbol_limit=args.cost_basis_symbol_limit,
        benchmark_index_symbols=tuple(_parse_symbol_text(args.benchmark_index_symbols)),
        benchmark_etf_symbols=tuple(_parse_symbol_text(args.benchmark_etf_symbols)),
        benchmark_start_date=args.benchmark_start_date or args.trade_date,
        structure_sector_name=args.structure_sector_name,
        structure_index_symbol=args.structure_index_symbol,
        structure_etf_market=args.structure_etf_market,
        structure_limit=args.structure_limit,
        structure_event_start_date=args.structure_event_start_date or args.trade_date,
        structure_event_end_date=args.structure_event_end_date or args.trade_date,
        include_turnover=not args.no_turnover,
    )
    report = execute_daily_market_structure_report(
        data_source=ConsolidatedMarketDataSource(),
        config=config,
    )
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "daily_market_structure_report.json"),
                "html": str(output_dir / "daily_market_structure_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] in {"completed", "partial"} else 1


def _write_outputs(*, output_dir: Path, report: dict) -> None:
    (output_dir / "daily_market_structure_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "daily_market_structure_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _resolve_symbol_inputs(
    *,
    symbols_text: str | None,
    symbols_file: Path | None,
    use_stock_metadata: bool,
) -> list[str] | None:
    if use_stock_metadata and (symbols_text or symbols_file):
        raise ValueError("--use-stock-metadata cannot be combined with explicit symbols")
    if use_stock_metadata:
        return None
    symbols = [
        *_parse_symbol_text(symbols_text or ""),
        *_parse_symbol_text(symbols_file.read_text(encoding="utf-8") if symbols_file else ""),
    ]
    return _unique_symbols(symbols) or list(DEFAULT_BREADTH_SYMBOLS)


def _parse_symbol_text(text: str) -> list[str]:
    normalized = text.replace("\n", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _unique_symbols(symbols: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for symbol in symbols:
        normalized = symbol.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _validate_positive(parser: argparse.ArgumentParser, name: str, value: int) -> None:
    if value <= 0:
        parser.error(f"--{name} must be positive")


def _default_output_dir() -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / "daily_market_structure" / timestamp


if __name__ == "__main__":
    raise SystemExit(main())
