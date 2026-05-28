from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.market_data_probe_common import (  # noqa: E402
    build_result,
    default_output_dir,
    report,
    summary,
    write_outputs,
)
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a gateway stock-sector membership probe."
    )
    parser.add_argument("--symbols", default="600519.SH,300024.SZ")
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--sector-types", default="concept")
    parser.add_argument("--limit-per-symbol", type=int, default=20)
    parser.add_argument("--sector-universe-limit", type=int)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbols = _parse_csv(args.symbols)
    sector_types = _parse_csv(args.sector_types)
    if not symbols:
        raise SystemExit("--symbols must contain at least one symbol")
    if not sector_types:
        raise SystemExit("--sector-types must contain at least one type")
    if args.limit_per_symbol <= 0:
        raise SystemExit("--limit-per-symbol must be positive")
    if args.sector_universe_limit is not None and args.sector_universe_limit < 0:
        raise SystemExit("--sector-universe-limit must be non-negative")
    output_dir = args.output_dir or default_output_dir("stock_sector_memberships_probe")
    source = ConsolidatedMarketDataSource()
    failures: list[dict[str, str]] = []
    try:
        rows = source.fetch_stock_sector_memberships(
            symbols=symbols,
            trade_date=args.trade_date,
            sector_types=sector_types,
            limit_per_symbol=args.limit_per_symbol,
            sector_universe_limit=args.sector_universe_limit,
        )
    except Exception as exc:
        rows = []
        failures.append({"capability": "stock_sector_membership", "reason": str(exc)})
    result = build_result(
        capability="stock_sector_membership",
        data_fetch_mode="gateway_provider_neutral",
        rows=rows,
        failures=failures,
        degradation_events=getattr(source, "degradation_events", []),
    )
    payload = report("stock-sector-memberships-probe-v1", result)
    write_outputs(
        output_dir,
        "stock_sector_memberships_report",
        "Stock Sector Memberships Probe",
        payload,
    )
    print(
        json.dumps(
            summary(output_dir, "stock_sector_memberships_report", result),
            ensure_ascii=False,
        )
    )
    return 0


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
