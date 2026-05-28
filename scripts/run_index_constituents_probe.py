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
    parser = argparse.ArgumentParser(description="Run a gateway index constituents probe.")
    parser.add_argument("--index-symbol", default="000300.SH")
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    output_dir = args.output_dir or default_output_dir("index_constituents_probe")
    source = ConsolidatedMarketDataSource()
    failures: list[dict[str, str]] = []
    try:
        rows = source.fetch_index_constituents(
            index_symbol=args.index_symbol,
            trade_date=args.trade_date,
            limit=args.limit,
        )
    except Exception as exc:
        rows = []
        failures.append({"capability": "index_constituents", "reason": str(exc)})
    result = build_result(
        capability="index_constituents",
        data_fetch_mode="gateway_provider_neutral",
        rows=rows,
        failures=failures,
        degradation_events=getattr(source, "degradation_events", []),
    )
    payload = report("index-constituents-probe-v1", result)
    write_outputs(output_dir, "index_constituents_report", "Index Constituents Probe", payload)
    print(json.dumps(summary(output_dir, "index_constituents_report", result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
