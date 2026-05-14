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

from scripts.validate_registry_rule_enriched_acceptance import (  # noqa: E402
    DEFAULT_ANNOUNCEMENT_START_DATE,
    DEFAULT_FUND_CODE,
    DEFAULT_MIN_ANNOUNCEMENT_COUNT,
    DEFAULT_MIN_QUOTE_COUNT,
    DEFAULT_STOCK_MAPPING_MODE,
    AcceptanceError,
)
from scripts.validate_registry_rule_enriched_acceptance import (  # noqa: E402
    validate_acceptance_outputs as validate_registry_rule_enriched_outputs,
)
from src import main as pipeline_main  # noqa: E402

DEFAULT_BASE_INTELLIGENCE_MODE = "provider-derived"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for enriched real provider-derived "
            "evidence/signals and registry-rule mappings."
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
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else Path(tempfile.mkdtemp(prefix="fni-provider-derived-enriched-"))
        )
        output_dir.mkdir(parents=True, exist_ok=True)
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
        print("Provider-derived enriched acceptance failed:", file=sys.stderr)
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
    require_news_evidence: bool = False,
) -> None:
    validate_registry_rule_enriched_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        min_announcement_count=min_announcement_count,
        min_quote_count=min_quote_count,
        base_intelligence_mode=DEFAULT_BASE_INTELLIGENCE_MODE,
    )
    raw = _read_json(output_dir / f"fund_{fund_code}_raw.json")
    scoring = _read_json(output_dir / f"fund_{fund_code}_scoring.json")
    markdown = (output_dir / f"fund_{fund_code}_report.md").read_text(encoding="utf-8")
    html = (output_dir / f"fund_{fund_code}_report.html").read_text(encoding="utf-8")
    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    evidence_layer = layers.get("evidence", {})
    signals_layer = layers.get("signals", {})
    evidence_items = raw.get("evidence") or []
    announcement_evidence_items = raw.get("announcement_evidence", {}).get("evidence") or []
    news_evidence = raw.get("news_evidence", {})
    news_evidence_items = news_evidence.get("evidence") or []
    signal_events = raw.get("signal_events") or []
    derived_signal_events = raw.get("derived_signal_events") or []

    _require(
        raw.get("base_intelligence_mode") == DEFAULT_BASE_INTELLIGENCE_MODE,
        "raw base_intelligence_mode must be provider-derived",
    )
    _require(
        scoring.get("base_intelligence_mode") == DEFAULT_BASE_INTELLIGENCE_MODE,
        "scoring base_intelligence_mode must be provider-derived",
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
        all(
            item.get("source") == "cninfo_announcement" or item.get("type") == "news"
            for item in evidence_items
        ),
        "evidence must come from provider-derived announcement or news sources",
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
        evidence_layer.get("provider_name") == "provider-derived-evidence",
        "evidence layer must use provider-derived-evidence",
    )
    _require(
        evidence_layer.get("data_quality") == "fresh",
        "evidence layer data_quality must be fresh",
    )
    _require(evidence_layer.get("is_mock") is False, "evidence layer must not be mock")
    _require(
        signals_layer.get("provider_name") == "provider-derived-signals",
        "signals layer must use provider-derived-signals",
    )
    _require(
        signals_layer.get("data_quality") == "fresh",
        "signals layer data_quality must be fresh",
    )
    _require(signals_layer.get("is_mock") is False, "signals layer must not be mock")
    expected = ("provider-derived-evidence", "provider-derived-signals", "Mock fixtures")
    _require(_contains_all(markdown, expected), "Markdown provider-derived disclosure mismatch")
    _require(_contains_all(html, expected), "HTML provider-derived disclosure mismatch")


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
    print("Provider-derived enriched acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print("stock_mapping_mode=registry-rule")
    print("base_intelligence_mode=provider-derived")
    print(f"announcement_start_date={announcement_start_date}")
    print(f"min_announcement_count={min_announcement_count}")
    print(f"min_quote_count={min_quote_count}")
    print("holdings=fresh")
    print("stock_mappings=registry_rule")
    print("evidence=provider_derived")
    print("signals=provider_derived")
    print("announcements=fresh")
    print("market_quotes=fresh")
    print("remaining_registry_layer=mock")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
