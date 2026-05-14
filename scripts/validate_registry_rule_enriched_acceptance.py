from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_real_enriched_acceptance import (  # noqa: E402
    DEFAULT_ANNOUNCEMENT_START_DATE,
    DEFAULT_FUND_CODE,
    DEFAULT_MIN_ANNOUNCEMENT_COUNT,
    DEFAULT_MIN_QUOTE_COUNT,
    AcceptanceError,
)
from scripts.validate_real_enriched_acceptance import (  # noqa: E402
    validate_acceptance_outputs as validate_real_enriched_outputs,
)
from src import main as pipeline_main  # noqa: E402

DEFAULT_STOCK_MAPPING_MODE = "registry-rule"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for the enriched real path with "
            "registry-rule stock mappings."
        )
    )
    parser.add_argument(
        "--fund-code",
        default=DEFAULT_FUND_CODE,
        help=f"Fund code to validate. Defaults to {DEFAULT_FUND_CODE}.",
    )
    parser.add_argument(
        "--announcement-start-date",
        default=DEFAULT_ANNOUNCEMENT_START_DATE,
        help=(
            "CNINFO announcement start date. Defaults to "
            f"{DEFAULT_ANNOUNCEMENT_START_DATE}."
        ),
    )
    parser.add_argument(
        "--min-announcement-count",
        type=int,
        default=DEFAULT_MIN_ANNOUNCEMENT_COUNT,
        help=(
            "Minimum announcement and evidence count. Defaults to "
            f"{DEFAULT_MIN_ANNOUNCEMENT_COUNT}."
        ),
    )
    parser.add_argument(
        "--min-quote-count",
        type=int,
        default=DEFAULT_MIN_QUOTE_COUNT,
        help=f"Minimum market quote count. Defaults to {DEFAULT_MIN_QUOTE_COUNT}.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. If omitted, a temporary directory is used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = Path(tempfile.mkdtemp(prefix="fni-registry-rule-enriched-"))

        _run_acceptance(
            fund_code=args.fund_code,
            announcement_start_date=args.announcement_start_date,
            min_announcement_count=args.min_announcement_count,
            min_quote_count=args.min_quote_count,
            output_dir=output_dir,
        )
        _print_success(
            fund_code=args.fund_code,
            announcement_start_date=args.announcement_start_date,
            min_announcement_count=args.min_announcement_count,
            min_quote_count=args.min_quote_count,
            output_dir=output_dir,
        )
        return 0
    except AcceptanceError as exc:
        print("Registry-rule enriched acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    announcement_start_date: str,
    min_announcement_count: int,
    min_quote_count: int,
    output_dir: Path,
) -> None:
    _run_cli(
        [
            "--fund-code",
            fund_code,
            "--provider-mode",
            "eastmoney",
            "--stock-mapping-mode",
            DEFAULT_STOCK_MAPPING_MODE,
            "--include-cninfo-announcements",
            "--announcement-start-date",
            announcement_start_date,
            "--include-market-quotes",
            "--output-dir",
            str(output_dir),
        ]
    )
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    validate_acceptance_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        min_announcement_count=min_announcement_count,
        min_quote_count=min_quote_count,
    )


def validate_acceptance_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
    min_announcement_count: int = DEFAULT_MIN_ANNOUNCEMENT_COUNT,
    min_quote_count: int = DEFAULT_MIN_QUOTE_COUNT,
) -> None:
    validate_real_enriched_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        min_announcement_count=min_announcement_count,
        min_quote_count=min_quote_count,
        stock_mapping_mode=DEFAULT_STOCK_MAPPING_MODE,
    )

    raw = _read_json(output_dir / f"fund_{fund_code}_raw.json")
    scoring = _read_json(output_dir / f"fund_{fund_code}_scoring.json")
    markdown = (output_dir / f"fund_{fund_code}_report.md").read_text(encoding="utf-8")
    html = (output_dir / f"fund_{fund_code}_report.html").read_text(encoding="utf-8")
    foundation = scoring.get("provider_foundation", {})
    mapping_layer = foundation.get("layers", {}).get("stock_mappings", {})
    mappings = raw.get("stock_narrative_mappings") or []
    coverage = raw.get("mapping_coverage", {})

    _require(
        raw.get("stock_mapping_mode") == DEFAULT_STOCK_MAPPING_MODE,
        "raw stock_mapping_mode must be registry-rule",
    )
    _require(
        scoring.get("stock_mapping_mode") == DEFAULT_STOCK_MAPPING_MODE,
        "scoring stock_mapping_mode must be registry-rule",
    )
    _require(
        raw.get("mapping_coverage") == scoring.get("mapping_coverage"),
        "scoring mapping coverage must match raw mapping coverage",
    )
    _require(
        isinstance(mappings, list) and len(mappings) > 0,
        "registry-rule acceptance requires selected mappings",
    )
    _require(
        all(item.get("method") == "registry_term_rule" for item in mappings),
        "all selected mappings must use registry_term_rule",
    )
    _require(
        set((coverage.get("mapping_methods") or {}).keys()) == {"registry_term_rule"},
        "mapping coverage methods must only contain registry_term_rule",
    )
    _require(
        mapping_layer.get("provider_name") == "registry-rule-stock-mapping",
        "stock mappings layer must use registry-rule-stock-mapping",
    )
    _require(
        mapping_layer.get("data_quality") == "partial",
        "stock mappings layer data_quality must be partial for real holdings plus mock registry",
    )
    _require(
        mapping_layer.get("source_url") == "derived://registry-term-rule-stock-mapping",
        "stock mappings layer source_url must identify registry-rule derivation",
    )
    _require(
        mapping_layer.get("is_mock") is False,
        "stock mappings layer must not be mock in real registry-rule mode",
    )
    _require(
        "registry-rule-stock-mapping" in str(foundation.get("disclosure_message") or ""),
        "provider disclosure must mention registry-rule-stock-mapping",
    )
    _require(
        "Narrative Registry" in str(foundation.get("disclosure_message") or ""),
        "provider disclosure must still mention mock Narrative Registry",
    )
    expected = ("registry-rule-stock-mapping", "Stock Mappings", "Mock fixtures")
    _require(_contains_all(markdown, expected), "Markdown registry-rule disclosure mismatch")
    _require(_contains_all(html, expected), "HTML registry-rule disclosure mismatch")


def _run_cli(args: list[str]) -> None:
    exit_code = pipeline_main.main(args)
    if exit_code != 0:
        raise AcceptanceError(
            f"command failed with exit code {exit_code}: python -m src.main {' '.join(args)}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AcceptanceError(f"{path} must contain a JSON object")
    return payload


def _contains_all(value: str, expected_fragments: tuple[str, ...]) -> bool:
    return all(fragment in value for fragment in expected_fragments)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def _print_success(
    fund_code: str,
    announcement_start_date: str,
    min_announcement_count: int,
    min_quote_count: int,
    output_dir: Path,
) -> None:
    print("Registry-rule enriched acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print("stock_mapping_mode=registry-rule")
    print(f"announcement_start_date={announcement_start_date}")
    print(f"min_announcement_count={min_announcement_count}")
    print(f"min_quote_count={min_quote_count}")
    print("holdings=fresh")
    print("stock_mappings=registry_rule")
    print("announcements=fresh")
    print("market_quotes=fresh")
    print("derived_signals=fresh")
    print("remaining_intelligence_layers=mock")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
