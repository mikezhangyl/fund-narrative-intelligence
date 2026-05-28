from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.scanners.breadth_scanner import (  # noqa: E402
    BreadthScanPlanner,
    execute_breadth_scan,
)

DEFAULT_SYMBOLS = ("600519.SH", "000001.SZ", "300750.SZ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a controlled deterministic market-breadth scan."
    )
    parser.add_argument(
        "--symbols",
        help=(
            "Comma-separated Tushare symbols. Defaults to a small controlled "
            f"universe: {','.join(DEFAULT_SYMBOLS)}."
        ),
    )
    parser.add_argument(
        "--symbols-file",
        type=Path,
        help="Optional file containing symbols separated by commas or newlines.",
    )
    parser.add_argument(
        "--use-stock-metadata",
        action="store_true",
        help="Resolve the symbol universe from provider stock metadata.",
    )
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--lookback-trading-days", type=int, default=60)
    parser.add_argument("--exchange", default="SSE")
    parser.add_argument("--analysis-capability", default="market_breadth_ma20")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Build the scan plan without fetching daily bars.",
    )
    parser.add_argument(
        "--no-turnover",
        action="store_true",
        help="Do not request turnover enrichment when fetching daily bars.",
    )
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.lookback_trading_days <= 0:
        parser.error("--lookback-trading-days must be positive")
    try:
        symbols = resolve_symbol_inputs(
            symbols_text=args.symbols,
            symbols_file=args.symbols_file,
            use_stock_metadata=args.use_stock_metadata,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_DIR
        / "breadth_scan"
        / datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        report = run_controlled_breadth_scan(
            data_source=ConsolidatedMarketDataSource(),
            symbols=symbols,
            end_date=args.end_date,
            lookback_trading_days=args.lookback_trading_days,
            exchange=args.exchange,
            analysis_capability=args.analysis_capability,
            plan_only=args.plan_only,
            include_turnover=not args.no_turnover,
        )
    except Exception as exc:
        report = {
            "version": "breadth-scan-v1",
            "generated_at": _utc_now(),
            "status": "failed",
            "failure_reason": str(exc),
        }
        _write_report(output_dir=output_dir, report=report)
        print(json.dumps({"output_dir": str(output_dir), "status": "failed"}))
        return 1

    _write_report(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "breadth_scan_report.json"),
                "markdown": str(output_dir / "breadth_scan_report.md"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] in {"completed", "planned"} else 1


def run_controlled_breadth_scan(
    *,
    data_source: Any,
    symbols: list[str] | None,
    end_date: str,
    lookback_trading_days: int = 60,
    exchange: str = "SSE",
    analysis_capability: str = "market_breadth_ma20",
    plan_only: bool = False,
    include_turnover: bool = True,
) -> dict[str, Any]:
    plan = BreadthScanPlanner().build_plan(
        data_source=data_source,
        symbols=symbols,
        end_date=end_date,
        lookback_trading_days=lookback_trading_days,
        exchange=exchange,
        analysis_capability=analysis_capability,
    )
    base_report: dict[str, Any] = {
        "version": "breadth-scan-v1",
        "generated_at": _utc_now(),
        "status": "blocked" if not plan.can_run else "planned",
        "scope": "controlled_breadth_scan",
        "plan_only": plan_only,
        "include_turnover": include_turnover,
        "scan_plan": plan.to_dict(),
        "data_fetch_mode": None,
        "bar_count": 0,
        "metrics": None,
    }
    if not plan.can_run or plan_only:
        return base_report

    result = execute_breadth_scan(
        data_source=data_source,
        plan=plan,
        include_turnover=include_turnover,
    )
    return {
        **base_report,
        "status": "completed",
        "data_fetch_mode": result.get("data_fetch_mode"),
        "bar_count": result["bar_count"],
        "metrics": result["metrics"],
    }


def resolve_symbol_inputs(
    *,
    symbols_text: str | None,
    symbols_file: Path | None,
    use_stock_metadata: bool,
) -> list[str] | None:
    if use_stock_metadata and (symbols_text or symbols_file):
        raise ValueError("--use-stock-metadata cannot be combined with explicit symbols")
    if use_stock_metadata:
        return None

    explicit_symbols = [
        *_parse_symbol_text(symbols_text or ""),
        *_parse_symbol_text(symbols_file.read_text(encoding="utf-8") if symbols_file else ""),
    ]
    return _unique_symbols(explicit_symbols) or list(DEFAULT_SYMBOLS)


def _write_report(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "breadth_scan_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "breadth_scan_report.md").write_text(
        _markdown_report(report),
        encoding="utf-8",
    )


def _markdown_report(report: dict[str, Any]) -> str:
    plan = report.get("scan_plan") if isinstance(report.get("scan_plan"), dict) else {}
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    lines = [
        "# Breadth Scan Report",
        "",
        f"- Status: `{report.get('status', '')}`",
        f"- Generated At: `{report.get('generated_at', '')}`",
        f"- Plan Only: `{report.get('plan_only', False)}`",
        f"- Symbols: `{len(plan.get('symbols', []))}`",
        f"- Window: `{plan.get('start_date', '')}` to `{plan.get('end_date', '')}`",
        f"- Data Fetch Mode: `{report.get('data_fetch_mode') or ''}`",
        f"- Bar Count: `{report.get('bar_count', 0)}`",
        "",
    ]
    blockers = plan.get("blockers", [])
    if blockers:
        lines.extend(["## Blockers", "", *[f"- `{blocker}`" for blocker in blockers], ""])
    if metrics:
        lines.extend(
            [
                "## Metrics",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Trade Date | {metrics.get('trade_date', '')} |",
                f"| Symbol Count | {metrics.get('symbol_count', 0)} |",
                f"| MA20 Breadth | {metrics.get('ma20_breadth', 0.0)} |",
                f"| Advance Count | {metrics.get('advance_count', 0)} |",
                f"| Decline Count | {metrics.get('decline_count', 0)} |",
                f"| New High Count | {metrics.get('new_high_count', 0)} |",
                f"| New Low Count | {metrics.get('new_low_count', 0)} |",
                f"| Volume Expansion | {metrics.get('volume_expansion', False)} |",
                "",
            ]
        )
    failure_reason = report.get("failure_reason")
    if failure_reason:
        lines.extend(["## Failure", "", str(failure_reason), ""])
    return "\n".join(lines)


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


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
