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

from scripts.validate_reviewed_registry_enriched_acceptance import (  # noqa: E402
    DEFAULT_ANNOUNCEMENT_START_DATE,
    DEFAULT_BASE_INTELLIGENCE_MODE,
    DEFAULT_FUND_CODE,
    DEFAULT_MIN_ANNOUNCEMENT_COUNT,
    DEFAULT_MIN_QUOTE_COUNT,
    DEFAULT_NARRATIVE_REGISTRY_MODE,
    AcceptanceError,
)
from scripts.validate_reviewed_registry_enriched_acceptance import (  # noqa: E402
    validate_acceptance_outputs as validate_reviewed_registry_outputs,
)
from src import main as pipeline_main  # noqa: E402
from src.config import (  # noqa: E402
    DEFAULT_REVIEWED_REGISTRY_PATH,
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
)

DEFAULT_STOCK_MAPPING_MODE = "reviewed"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for enriched real providers with reviewed "
            "registry and reviewed stock mappings."
        )
    )
    parser.add_argument("--fund-code", default=DEFAULT_FUND_CODE)
    parser.add_argument(
        "--announcement-start-date",
        default=DEFAULT_ANNOUNCEMENT_START_DATE,
    )
    parser.add_argument(
        "--min-announcement-count",
        type=int,
        default=DEFAULT_MIN_ANNOUNCEMENT_COUNT,
    )
    parser.add_argument(
        "--min-quote-count",
        type=int,
        default=DEFAULT_MIN_QUOTE_COUNT,
    )
    parser.add_argument(
        "--narrative-registry-path",
        type=Path,
        default=DEFAULT_REVIEWED_REGISTRY_PATH,
    )
    parser.add_argument(
        "--stock-mappings-path",
        type=Path,
        default=DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    )
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else Path(tempfile.mkdtemp(prefix="fni-reviewed-mapping-enriched-"))
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        _run_acceptance(
            fund_code=args.fund_code,
            announcement_start_date=args.announcement_start_date,
            min_announcement_count=args.min_announcement_count,
            min_quote_count=args.min_quote_count,
            narrative_registry_path=args.narrative_registry_path,
            stock_mappings_path=args.stock_mappings_path,
            output_dir=output_dir,
        )
        _print_success(
            fund_code=args.fund_code,
            announcement_start_date=args.announcement_start_date,
            min_announcement_count=args.min_announcement_count,
            min_quote_count=args.min_quote_count,
            narrative_registry_path=args.narrative_registry_path,
            stock_mappings_path=args.stock_mappings_path,
            output_dir=output_dir,
        )
        return 0
    except AcceptanceError as exc:
        print("Reviewed-mapping enriched acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    announcement_start_date: str,
    min_announcement_count: int,
    min_quote_count: int,
    narrative_registry_path: Path,
    stock_mappings_path: Path,
    output_dir: Path,
) -> None:
    _run_cli(
        [
            "--fund-code",
            fund_code,
            "--provider-mode",
            "eastmoney",
            "--narrative-registry-mode",
            DEFAULT_NARRATIVE_REGISTRY_MODE,
            "--narrative-registry-path",
            str(narrative_registry_path),
            "--stock-mapping-mode",
            DEFAULT_STOCK_MAPPING_MODE,
            "--stock-mappings-path",
            str(stock_mappings_path),
            "--base-intelligence-mode",
            DEFAULT_BASE_INTELLIGENCE_MODE,
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
    validate_reviewed_registry_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        min_announcement_count=min_announcement_count,
        min_quote_count=min_quote_count,
        stock_mapping_mode=DEFAULT_STOCK_MAPPING_MODE,
        stock_mapping_provider_name="reviewed-mapping-store",
        stock_mapping_method="reviewed_mapping",
    )
    raw = _read_json(output_dir / f"fund_{fund_code}_raw.json")
    scoring = _read_json(output_dir / f"fund_{fund_code}_scoring.json")
    markdown = (output_dir / f"fund_{fund_code}_report.md").read_text(encoding="utf-8")
    html = (output_dir / f"fund_{fund_code}_report.html").read_text(encoding="utf-8")
    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    mapping_layer = layers.get("stock_mappings", {})
    mappings = raw.get("stock_narrative_mappings") or []
    coverage = raw.get("mapping_coverage", {})

    _require(
        raw.get("stock_mapping_mode") == DEFAULT_STOCK_MAPPING_MODE,
        "raw stock_mapping_mode must be reviewed",
    )
    _require(
        scoring.get("stock_mapping_mode") == DEFAULT_STOCK_MAPPING_MODE,
        "scoring stock_mapping_mode must be reviewed",
    )
    _require(
        isinstance(mappings, list) and mappings,
        "reviewed mapping acceptance requires selected mappings",
    )
    _require(
        all(item.get("method") == "reviewed_mapping" for item in mappings),
        "all selected mappings must use reviewed_mapping",
    )
    _require(
        set((coverage.get("mapping_methods") or {}).keys()) == {"reviewed_mapping"},
        "mapping coverage methods must only contain reviewed_mapping",
    )
    _require(
        mapping_layer.get("provider_name") == "reviewed-mapping-store",
        "stock mappings layer must use reviewed-mapping-store",
    )
    _require(
        mapping_layer.get("data_quality") == "partial",
        "stock mappings layer data_quality must be partial for V1 reviewed store",
    )
    _require(
        mapping_layer.get("is_mock") is False,
        "stock mappings layer must not be mock",
    )
    _require(
        str(mapping_layer.get("source_url") or "").startswith("reviewed-mapping://"),
        "stock mappings layer source_url must use reviewed-mapping://",
    )
    _require(
        "#sha256=" in str(mapping_layer.get("source_url") or ""),
        "stock mappings layer source_url must include a content hash",
    )
    expected = (
        "reviewed-registry-store",
        "reviewed-mapping-store",
        "provider-derived-evidence",
        "provider-derived-signals",
    )
    _require(_contains_all(markdown, expected), "Markdown reviewed mapping mismatch")
    _require(_contains_all(html, expected), "HTML reviewed mapping mismatch")
    _require("Mock fixtures" not in markdown, "Markdown must not label path as mock")
    _require("Mock fixtures" not in html, "HTML must not label path as mock")


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
    narrative_registry_path: Path,
    stock_mappings_path: Path,
    output_dir: Path,
) -> None:
    print("Reviewed-mapping enriched acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print("narrative_registry_mode=reviewed")
    print(f"narrative_registry_path={narrative_registry_path}")
    print("stock_mapping_mode=reviewed")
    print(f"stock_mappings_path={stock_mappings_path}")
    print("base_intelligence_mode=provider-derived")
    print(f"announcement_start_date={announcement_start_date}")
    print(f"min_announcement_count={min_announcement_count}")
    print(f"min_quote_count={min_quote_count}")
    print("holdings=fresh")
    print("narrative_registry=reviewed")
    print("stock_mappings=reviewed")
    print("evidence=provider_derived")
    print("signals=provider_derived")
    print("announcements=fresh")
    print("market_quotes=fresh")
    print("mock_layers=none")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
