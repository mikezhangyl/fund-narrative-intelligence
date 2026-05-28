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
    parser = argparse.ArgumentParser(description="Run a gateway CYQ chips probe.")
    parser.add_argument("--symbols", default="600519.SH")
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbols = _parse_symbols(args.symbols)
    if not symbols:
        raise SystemExit("--symbols must contain at least one symbol")
    output_dir = args.output_dir or default_output_dir("cyq_chips_probe")
    source = ConsolidatedMarketDataSource()
    failures: list[dict[str, str]] = []
    try:
        rows = source.fetch_cyq_chips(
            symbols=symbols,
            trade_date=args.trade_date,
        )
    except Exception as exc:
        rows = []
        failures.append({"capability": "cyq_chips", "reason": str(exc)})
    result = build_result(
        capability="cyq_chips",
        data_fetch_mode="gateway_provider_neutral",
        rows=rows,
        failures=failures,
        degradation_events=getattr(source, "degradation_events", []),
    )
    payload = report("cyq-chips-probe-v1", result)
    write_outputs(output_dir, "cyq_chips_report", "CYQ Chips Probe", payload)
    print(json.dumps(summary(output_dir, "cyq_chips_report", result), ensure_ascii=False))
    return 0


def _parse_symbols(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
