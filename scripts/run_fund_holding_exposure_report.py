from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.providers.intelligence import (  # noqa: E402
    MockNarrativeRegistryProvider,
    MockStockNarrativeMappingProvider,
    ReviewedNarrativeRegistryProvider,
    ReviewedStockNarrativeMappingProvider,
)
from src.providers.narrative_service import (  # noqa: E402
    LocalNarrativePrototypeProvider,
)
from src.scanners.fund_holding_exposure_report import (  # noqa: E402
    FundHoldingExposureConfig,
    execute_fund_holding_exposure_report,
    render_html_report,
)

INTELLIGENCE_MODES = ("fixture", "reviewed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Can-Do fund holding exposure report."
    )
    parser.add_argument("--fund-code", default="161725")
    parser.add_argument("--sector-trade-date")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sector-types", default="concept")
    parser.add_argument("--limit-per-symbol", type=int, default=50)
    parser.add_argument("--sector-universe-limit", type=int)
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
    fund_code = args.fund_code.strip()
    sector_types = _parse_csv(args.sector_types)
    if not fund_code:
        raise SystemExit("--fund-code must be non-empty")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.limit_per_symbol <= 0:
        raise SystemExit("--limit-per-symbol must be positive")
    if args.sector_universe_limit is not None and args.sector_universe_limit < 0:
        raise SystemExit("--sector-universe-limit must be non-negative")
    if not sector_types:
        raise SystemExit("--sector-types must contain at least one type")
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR / "fund_holding_exposure"
    output_dir.mkdir(parents=True, exist_ok=True)
    narrative_registry, stock_mappings = load_intelligence_context(
        registry_mode=args.narrative_registry_mode,
        stock_mapping_mode=args.stock_mapping_mode,
    )
    report = execute_fund_holding_exposure_report(
        data_source=ConsolidatedMarketDataSource(),
        config=FundHoldingExposureConfig(
            fund_code=fund_code,
            sector_trade_date=args.sector_trade_date,
            limit=args.limit,
            sector_types=tuple(sector_types),
            limit_per_symbol=args.limit_per_symbol,
            sector_universe_limit=args.sector_universe_limit,
        ),
        narrative_registry=narrative_registry,
        stock_narrative_mappings=stock_mappings,
    )
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "fund_holding_exposure_report.json"),
                "html": str(output_dir / "fund_holding_exposure_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] in {"completed", "partial", "missing"} else 1


def load_intelligence_context(
    *,
    registry_mode: str,
    stock_mapping_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if registry_mode == "reviewed" and stock_mapping_mode == "reviewed":
        return LocalNarrativePrototypeProvider().get_report_inputs()
    registry_provider = (
        ReviewedNarrativeRegistryProvider()
        if registry_mode == "reviewed"
        else MockNarrativeRegistryProvider()
    )
    mapping_provider = (
        ReviewedStockNarrativeMappingProvider()
        if stock_mapping_mode == "reviewed"
        else MockStockNarrativeMappingProvider()
    )
    return (
        registry_provider.get_narrative_registry(),
        mapping_provider.get_stock_narrative_mappings(),
    )


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "fund_holding_exposure_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "fund_holding_exposure_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
