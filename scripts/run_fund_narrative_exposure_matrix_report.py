from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_fund_holding_exposure_report import (  # noqa: E402
    INTELLIGENCE_MODES,
    _normalize_context,
    load_intelligence_context,
)
from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.scanners.fund_narrative_exposure_matrix_report import (  # noqa: E402
    FundNarrativeExposureMatrixConfig,
    execute_fund_narrative_exposure_matrix_report,
    render_html_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Can-Do fund narrative exposure matrix report."
    )
    parser.add_argument("--fund-codes", required=True)
    parser.add_argument("--sector-trade-date")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sector-types", default="concept")
    parser.add_argument("--limit-per-symbol", type=int, default=50)
    parser.add_argument("--sector-universe-limit", type=int)
    parser.add_argument("--exposure-floor", type=float, default=0.0)
    parser.add_argument("--high-similarity-threshold", type=float, default=0.85)
    parser.add_argument(
        "--narrative-registry-mode",
        choices=INTELLIGENCE_MODES,
        default="reviewed",
    )
    parser.add_argument(
        "--stock-mapping-mode",
        choices=INTELLIGENCE_MODES,
        default="reviewed",
    )
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fund_codes = _parse_csv(args.fund_codes)
    sector_types = _parse_csv(args.sector_types)
    if len(fund_codes) < 2:
        raise SystemExit("--fund-codes must contain at least two fund codes")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.limit_per_symbol <= 0:
        raise SystemExit("--limit-per-symbol must be positive")
    if args.sector_universe_limit is not None and args.sector_universe_limit < 0:
        raise SystemExit("--sector-universe-limit must be non-negative")
    if args.exposure_floor < 0:
        raise SystemExit("--exposure-floor must be non-negative")
    if not 0 <= args.high_similarity_threshold <= 1:
        raise SystemExit("--high-similarity-threshold must be between 0 and 1")
    if not sector_types:
        raise SystemExit("--sector-types must contain at least one type")
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR / "fund_narrative_exposure_matrix"
    output_dir.mkdir(parents=True, exist_ok=True)
    narrative_registry, stock_mappings, narrative_source = _normalize_context(
        load_intelligence_context(
            registry_mode=args.narrative_registry_mode,
            stock_mapping_mode=args.stock_mapping_mode,
        )
    )
    report = execute_fund_narrative_exposure_matrix_report(
        data_source=ConsolidatedMarketDataSource(),
        config=FundNarrativeExposureMatrixConfig(
            fund_codes=tuple(fund_codes),
            sector_trade_date=args.sector_trade_date,
            limit=args.limit,
            sector_types=tuple(sector_types),
            limit_per_symbol=args.limit_per_symbol,
            sector_universe_limit=args.sector_universe_limit,
            exposure_floor=args.exposure_floor,
            high_similarity_threshold=args.high_similarity_threshold,
        ),
        narrative_registry=narrative_registry,
        stock_narrative_mappings=stock_mappings,
        narrative_source=narrative_source,
    )
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "fund_narrative_exposure_matrix_report.json"),
                "html": str(output_dir / "fund_narrative_exposure_matrix_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] in {"completed", "partial", "missing"} else 1


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "fund_narrative_exposure_matrix_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "fund_narrative_exposure_matrix_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
