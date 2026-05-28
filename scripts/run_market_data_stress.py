from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_breadth_scan import resolve_symbol_inputs  # noqa: E402
from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.market_data.stress import MarketDataStressTester  # noqa: E402

DEFAULT_ETF_SYMBOLS = ("510300.SH", "159915.SZ")
STRESS_MODES = ("historical", "daily", "sector")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run controlled V0 market-data stress probes."
    )
    parser.add_argument(
        "--mode",
        choices=(*STRESS_MODES, "all"),
        default="all",
        help="Stress probe to run. Defaults to all V0 probes.",
    )
    parser.add_argument("--symbols")
    parser.add_argument("--symbols-file", type=Path)
    parser.add_argument("--use-stock-metadata", action="store_true")
    parser.add_argument("--max-symbols", type=int, default=100)
    parser.add_argument("--etf-symbols", default=",".join(DEFAULT_ETF_SYMBOLS))
    parser.add_argument("--start-date", default="2026-05-18")
    parser.add_argument("--end-date", default="2026-05-22")
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_symbols <= 0:
        parser.error("--max-symbols must be positive")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    try:
        symbol_input = resolve_symbol_inputs(
            symbols_text=args.symbols,
            symbols_file=args.symbols_file,
            use_stock_metadata=args.use_stock_metadata,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_DIR
        / "market_data_stress"
        / datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    data_source = ConsolidatedMarketDataSource()
    symbols = resolve_stress_symbols(
        data_source=data_source,
        symbol_input=symbol_input,
        max_symbols=args.max_symbols,
    )
    report = run_stress_suite(
        provider=data_source,
        symbols=symbols,
        etf_symbols=resolve_etf_symbols(args.etf_symbols),
        start_date=args.start_date,
        end_date=args.end_date,
        trade_date=args.trade_date,
        modes=_resolve_modes(args.mode),
        batch_size=args.batch_size,
    )
    _write_report(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "stress_report.json"),
                "markdown": str(output_dir / "stress_report.md"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def run_stress_suite(
    *,
    provider: Any,
    symbols: list[str],
    etf_symbols: list[str],
    start_date: str,
    end_date: str,
    trade_date: str,
    modes: tuple[str, ...],
    batch_size: int,
) -> dict[str, Any]:
    tester = MarketDataStressTester(provider=provider, batch_size=batch_size)
    results: dict[str, dict[str, Any]] = {}
    if "historical" in modes:
        results["historical"] = tester.run_historical_scan(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        ).to_dict()
    if "daily" in modes:
        results["daily"] = tester.run_incremental_daily_update(
            symbols=symbols,
            trade_date=trade_date,
        ).to_dict()
    if "sector" in modes:
        results["sector"] = tester.run_sector_rotation_scan(
            etf_symbols=etf_symbols,
            trade_date=trade_date,
        ).to_dict()

    summary = _summarize_results(results)
    return {
        "version": "market-data-stress-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "completed_with_failures"
        if summary["failure_count"] > 0
        else "completed",
        "scope": "controlled_v0_stress_probe",
        "plan": {
            "modes": list(modes),
            "symbol_count": len(symbols),
            "etf_symbol_count": len(etf_symbols),
            "start_date": start_date,
            "end_date": end_date,
            "trade_date": trade_date,
            "batch_size": batch_size,
        },
        "summary": summary,
        "results": results,
    }


def resolve_stress_symbols(
    *,
    data_source: Any,
    symbol_input: list[str] | None,
    max_symbols: int,
) -> list[str]:
    if symbol_input is not None:
        return symbol_input[:max_symbols]
    rows = data_source.fetch_stock_metadata()
    symbols = [
        str(row.get("ts_code") or row.get("symbol") or "").strip()
        for row in rows
        if row.get("ts_code") or row.get("symbol")
    ]
    return symbols[:max_symbols]


def resolve_etf_symbols(text: str) -> list[str]:
    symbols = [part.strip() for part in text.replace("\n", ",").split(",")]
    return [symbol for symbol in symbols if symbol]


def _resolve_modes(mode: str) -> tuple[str, ...]:
    return STRESS_MODES if mode == "all" else (mode,)


def _summarize_results(results: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {
        "test_count": len(results),
        "request_volume": sum(int(item.get("request_volume", 0)) for item in results.values()),
        "rows_returned": sum(int(item.get("rows_returned", 0)) for item in results.values()),
        "failure_count": sum(int(item.get("failure_count", 0)) for item in results.values()),
        "throttling_events": sum(
            int(item.get("throttling_events", 0)) for item in results.values()
        ),
    }


def _write_report(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "stress_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "stress_report.md").write_text(
        _markdown_report(report),
        encoding="utf-8",
    )


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    results = report.get("results", {})
    lines = [
        "# Market Data Stress Report",
        "",
        f"- Status: `{report.get('status', '')}`",
        f"- Generated At: `{report.get('generated_at', '')}`",
        f"- Tests: `{summary.get('test_count', 0)}`",
        f"- Requests: `{summary.get('request_volume', 0)}`",
        f"- Rows Returned: `{summary.get('rows_returned', 0)}`",
        f"- Failures: `{summary.get('failure_count', 0)}`",
        "",
        "| Test | Requests | Rows | Failures | Memory KB |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, result in results.items():
        lines.append(
            "| "
            f"{name} | "
            f"{result.get('request_volume', 0)} | "
            f"{result.get('rows_returned', 0)} | "
            f"{result.get('failure_count', 0)} | "
            f"{result.get('peak_memory_kb', 0)} |"
        )
    failure_lines = [
        f"- `{name}`: {reason}"
        for name, result in results.items()
        for reason in result.get("failure_reasons", [])
    ]
    if failure_lines:
        lines.extend(["", "## Failure Reasons", "", *failure_lines])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
