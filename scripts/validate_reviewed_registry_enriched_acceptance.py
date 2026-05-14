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
    REAL_QUOTE_PROVIDERS,
    AcceptanceError,
)
from src import main as pipeline_main  # noqa: E402
from src.config import DEFAULT_REVIEWED_REGISTRY_PATH  # noqa: E402

DEFAULT_NARRATIVE_REGISTRY_MODE = "reviewed"
DEFAULT_STOCK_MAPPING_MODE = "registry-rule"
DEFAULT_BASE_INTELLIGENCE_MODE = "provider-derived"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for enriched real providers with a "
            "reviewed Narrative Registry store."
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
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else Path(tempfile.mkdtemp(prefix="fni-reviewed-registry-enriched-"))
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        _run_acceptance(
            fund_code=args.fund_code,
            announcement_start_date=args.announcement_start_date,
            min_announcement_count=args.min_announcement_count,
            min_quote_count=args.min_quote_count,
            narrative_registry_path=args.narrative_registry_path,
            output_dir=output_dir,
        )
        _print_success(
            fund_code=args.fund_code,
            announcement_start_date=args.announcement_start_date,
            min_announcement_count=args.min_announcement_count,
            min_quote_count=args.min_quote_count,
            narrative_registry_path=args.narrative_registry_path,
            output_dir=output_dir,
        )
        return 0
    except AcceptanceError as exc:
        print("Reviewed-registry enriched acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    announcement_start_date: str,
    min_announcement_count: int,
    min_quote_count: int,
    narrative_registry_path: Path,
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
            "--base-intelligence-mode",
            DEFAULT_BASE_INTELLIGENCE_MODE,
            "--include-cninfo-announcements",
            "--announcement-start-date",
            announcement_start_date,
            "--include-market-quotes",
            "--include-news-evidence",
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
        require_news_evidence=True,
    )


def validate_acceptance_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
    min_announcement_count: int = DEFAULT_MIN_ANNOUNCEMENT_COUNT,
    min_quote_count: int = DEFAULT_MIN_QUOTE_COUNT,
    stock_mapping_mode: str = DEFAULT_STOCK_MAPPING_MODE,
    stock_mapping_provider_name: str = "registry-rule-stock-mapping",
    stock_mapping_method: str = "registry_term_rule",
    require_news_evidence: bool = False,
) -> None:
    artifacts = {
        "raw": output_dir / f"fund_{fund_code}_raw.json",
        "scoring": output_dir / f"fund_{fund_code}_scoring.json",
        "source_table": output_dir / f"fund_{fund_code}_source_table.json",
        "manifest": output_dir / f"fund_{fund_code}_manifest.json",
        "markdown": output_dir / f"fund_{fund_code}_report.md",
        "html": output_dir / f"fund_{fund_code}_report.html",
    }
    for key, path in artifacts.items():
        _require(path.is_file(), f"missing {key} artifact: {path}")

    raw = _read_json(artifacts["raw"])
    scoring = _read_json(artifacts["scoring"])
    source_table = _read_json(artifacts["source_table"])
    manifest = _read_json(artifacts["manifest"])
    markdown = artifacts["markdown"].read_text(encoding="utf-8")
    html = artifacts["html"].read_text(encoding="utf-8")
    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    registry_layer = layers.get("narrative_registry", {})
    mapping_layer = layers.get("stock_mappings", {})
    evidence_layer = layers.get("evidence", {})
    signals_layer = layers.get("signals", {})
    announcement_items = raw.get("announcements", {}).get("announcements") or []
    quotes = raw.get("market_quotes", {}).get("quotes") or []
    mappings = raw.get("stock_narrative_mappings") or []
    evidence_items = raw.get("evidence") or []
    announcement_evidence_items = raw.get("announcement_evidence", {}).get("evidence") or []
    news_evidence = raw.get("news_evidence", {})
    news_evidence_items = news_evidence.get("evidence") or []
    signal_events = raw.get("signal_events") or []
    derived_signal_events = raw.get("derived_signal_events") or []

    _require(raw.get("metadata", {}).get("fund_code") == fund_code, "raw fund_code mismatch")
    _require(raw.get("provider_foundation") == foundation, "raw/scoring foundation mismatch")
    _require(manifest.get("provider_foundation") == foundation, "manifest foundation mismatch")
    _require(source_table.get("fund_code") == fund_code, "source table fund_code mismatch")
    _require(
        source_table.get("provider_foundation") == foundation,
        "source table provider_foundation mismatch",
    )
    _require(
        raw.get("narrative_registry_mode") == DEFAULT_NARRATIVE_REGISTRY_MODE,
        "raw narrative_registry_mode must be reviewed",
    )
    _require(
        scoring.get("narrative_registry_mode") == DEFAULT_NARRATIVE_REGISTRY_MODE,
        "scoring narrative_registry_mode must be reviewed",
    )
    _require(
        raw.get("stock_mapping_mode") == stock_mapping_mode,
        f"raw stock_mapping_mode must be {stock_mapping_mode}",
    )
    _require(
        scoring.get("stock_mapping_mode") == stock_mapping_mode,
        f"scoring stock_mapping_mode must be {stock_mapping_mode}",
    )
    _require(
        raw.get("base_intelligence_mode") == DEFAULT_BASE_INTELLIGENCE_MODE,
        "raw base_intelligence_mode must be provider-derived",
    )
    _require(
        registry_layer.get("provider_name") == "reviewed-registry-store",
        "Narrative Registry layer must use reviewed-registry-store",
    )
    _require(registry_layer.get("data_quality") == "fresh", "registry layer must be fresh")
    _require(registry_layer.get("is_mock") is False, "registry layer must not be mock")
    _require(
        str(registry_layer.get("source_url") or "").startswith("reviewed-registry://"),
        "registry layer source_url must use reviewed-registry://",
    )
    _require(
        "#sha256=" in str(registry_layer.get("source_url") or ""),
        "registry layer source_url must include a content hash",
    )
    _require(
        mapping_layer.get("provider_name") == stock_mapping_provider_name,
        f"stock mappings layer must use {stock_mapping_provider_name}",
    )
    _require(mapping_layer.get("is_mock") is False, "stock mappings layer must not be mock")
    _require(
        evidence_layer.get("provider_name") == "provider-derived-evidence",
        "evidence layer must use provider-derived-evidence",
    )
    _require(evidence_layer.get("is_mock") is False, "evidence layer must not be mock")
    _require(
        signals_layer.get("provider_name") == "provider-derived-signals",
        "signals layer must use provider-derived-signals",
    )
    _require(signals_layer.get("is_mock") is False, "signals layer must not be mock")
    _require(
        layers.get("holdings", {}).get("data_quality") == "fresh",
        "holdings layer must be fresh",
    )
    _require(
        layers.get("announcements", {}).get("data_quality") == "fresh",
        "announcements layer must be fresh",
    )
    _require(
        layers.get("market_quotes", {}).get("provider_name") in REAL_QUOTE_PROVIDERS,
        "market quotes layer must use a real quote provider",
    )
    _require(
        isinstance(announcement_items, list)
        and len(announcement_items) >= min_announcement_count,
        f"announcement count must be at least {min_announcement_count}",
    )
    _require(
        isinstance(quotes, list) and len(quotes) >= min_quote_count,
        f"market quote count must be at least {min_quote_count}",
    )
    _require(
        isinstance(mappings, list) and mappings,
        f"{stock_mapping_mode} acceptance requires selected mappings",
    )
    _require(
        all(item.get("method") == stock_mapping_method for item in mappings),
        f"all selected mappings must use {stock_mapping_method}",
    )
    _require(
        evidence_items == [*announcement_evidence_items, *news_evidence_items],
        "evidence must match provider-derived evidence records",
    )
    if require_news_evidence:
        _require(isinstance(news_evidence, dict) and news_evidence, "news_evidence is required")
        _require(
            layers.get("news_evidence", {}).get("is_mock") is False,
            "news evidence layer must not be mock",
        )
    _require(
        signal_events == derived_signal_events,
        "signal_events must match derived_signal_events",
    )
    _require(
        signal_events == scoring.get("derived_signal_events"),
        "scoring derived signals must match raw signal events",
    )
    _require(
        all(not layer.get("is_mock") for layer in layers.values()),
        "reviewed enriched path must not contain mock provider foundation layers",
    )
    expected = (
        "reviewed-registry-store",
        stock_mapping_provider_name,
        "provider-derived-evidence",
        "provider-derived-signals",
    )
    _require(_contains_all(markdown, expected), "Markdown reviewed disclosure mismatch")
    _require(_contains_all(html, expected), "HTML reviewed disclosure mismatch")
    _require("Mock fixtures" not in markdown, "Markdown must not label reviewed path as mock")
    _require("Mock fixtures" not in html, "HTML must not label reviewed path as mock")


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
    output_dir: Path,
) -> None:
    print("Reviewed-registry enriched acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print("narrative_registry_mode=reviewed")
    print(f"narrative_registry_path={narrative_registry_path}")
    print("stock_mapping_mode=registry-rule")
    print("base_intelligence_mode=provider-derived")
    print(f"announcement_start_date={announcement_start_date}")
    print(f"min_announcement_count={min_announcement_count}")
    print(f"min_quote_count={min_quote_count}")
    print("holdings=fresh")
    print("narrative_registry=reviewed")
    print("stock_mappings=registry_rule")
    print("evidence=provider_derived")
    print("signals=provider_derived")
    print("announcements=fresh")
    print("market_quotes=fresh")
    print("mock_layers=none")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
