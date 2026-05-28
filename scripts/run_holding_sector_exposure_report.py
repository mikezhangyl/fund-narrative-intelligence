from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.scanners.holding_sector_exposure_report import (  # noqa: E402
    HoldingSectorExposureConfig,
    execute_holding_sector_exposure_report,
    render_html_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Can-Do holding sector exposure report."
    )
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--sector-types", default="concept")
    parser.add_argument("--limit-per-symbol", type=int, default=50)
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
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR / "holding_sector_exposure"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = execute_holding_sector_exposure_report(
        data_source=ConsolidatedMarketDataSource(),
        config=HoldingSectorExposureConfig(
            symbols=tuple(symbols),
            trade_date=args.trade_date,
            sector_types=tuple(sector_types),
            limit_per_symbol=args.limit_per_symbol,
            sector_universe_limit=args.sector_universe_limit,
        ),
    )
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "holding_sector_exposure_report.json"),
                "html": str(output_dir / "holding_sector_exposure_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] in {"completed", "partial", "missing"} else 1


def _write_outputs(*, output_dir: Path, report: dict) -> None:
    (output_dir / "holding_sector_exposure_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "holding_sector_exposure_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
