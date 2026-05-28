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
from src.scanners.structure_mapping_report import (  # noqa: E402
    StructureMappingReportConfig,
    execute_structure_mapping_report,
    render_html_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Can-Do market structure mapping report."
    )
    parser.add_argument("--trade-date", default=date.today().isoformat())
    parser.add_argument("--sector-name", default="机器人")
    parser.add_argument("--index-symbol", default="000300.SH")
    parser.add_argument("--event-start-date")
    parser.add_argument("--event-end-date")
    parser.add_argument("--etf-market", default="cn")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit <= 0:
        parser.error("--limit must be positive")
    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = StructureMappingReportConfig(
        trade_date=args.trade_date,
        sector_name=args.sector_name,
        index_symbol=args.index_symbol,
        event_start_date=args.event_start_date or args.trade_date,
        event_end_date=args.event_end_date or args.trade_date,
        etf_market=args.etf_market,
        limit=args.limit,
    )
    report = execute_structure_mapping_report(
        data_source=ConsolidatedMarketDataSource(),
        config=config,
    )
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "structure_mapping_report.json"),
                "html": str(output_dir / "structure_mapping_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] in {"completed", "partial"} else 1


def _write_outputs(*, output_dir: Path, report: dict) -> None:
    (output_dir / "structure_mapping_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "structure_mapping_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _default_output_dir() -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / "structure_mapping_report" / timestamp


if __name__ == "__main__":
    raise SystemExit(main())
