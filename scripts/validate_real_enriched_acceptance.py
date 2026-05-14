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

from src import main as pipeline_main  # noqa: E402
from src.providers.cninfo import CNINFO_ANNOUNCEMENT_QUERY_URL  # noqa: E402
from src.providers.eastmoney import EASTMONEY_HOLDINGS_URL  # noqa: E402

DEFAULT_FUND_CODE = "161725"
DEFAULT_ANNOUNCEMENT_START_DATE = "2026-01-01"
DEFAULT_MIN_ANNOUNCEMENT_COUNT = 1
DEFAULT_MIN_QUOTE_COUNT = 1
REAL_QUOTE_PROVIDERS = {
    "eastmoney-market-quote",
    "yahoo-chart",
    "mixed-market-quote",
}
REAL_QUOTE_SOURCE_PROVIDERS = {"eastmoney", "yahoo-chart"}


class AcceptanceError(RuntimeError):
    """Raised when the enriched real acceptance contract is not satisfied."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for Eastmoney holdings, CNINFO "
            "announcements, market quotes, and derived signals."
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

        output_dir = Path(tempfile.mkdtemp(prefix="fni-real-enriched-"))
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
        print("Real enriched acceptance failed:", file=sys.stderr)
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
    artifacts = {
        "raw": output_dir / f"fund_{fund_code}_raw.json",
        "scoring": output_dir / f"fund_{fund_code}_scoring.json",
        "review_queue": output_dir / f"fund_{fund_code}_review_queue.json",
        "manifest": output_dir / f"fund_{fund_code}_manifest.json",
        "markdown": output_dir / f"fund_{fund_code}_report.md",
        "html": output_dir / f"fund_{fund_code}_report.html",
    }
    for key, path in artifacts.items():
        if not path.is_file():
            raise AcceptanceError(f"missing {key} artifact: {path}")

    raw = _read_json(artifacts["raw"])
    scoring = _read_json(artifacts["scoring"])
    manifest = _read_json(artifacts["manifest"])
    review_queue = _read_json(artifacts["review_queue"])
    markdown = artifacts["markdown"].read_text(encoding="utf-8")
    html = artifacts["html"].read_text(encoding="utf-8")

    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    raw_provider = raw.get("fund", {}).get("provider_metadata", {})
    announcements = raw.get("announcements", {})
    announcement_items = announcements.get("announcements") or []
    raw_announcement_evidence = raw.get("announcement_evidence", {})
    scoring_announcement_evidence = scoring.get("announcement_evidence", {})
    raw_evidence = raw_announcement_evidence.get("evidence") or []
    raw_market_quotes = raw.get("market_quotes", {})
    scoring_market_quotes = scoring.get("market_quotes", {})
    quotes = raw_market_quotes.get("quotes") or []
    raw_derived_signals = raw.get("derived_signal_events") or []
    scoring_derived_signals = scoring.get("derived_signal_events") or []
    degradation_events = scoring.get("degradation_events") or []

    _require(raw.get("metadata", {}).get("fund_code") == fund_code, "raw fund_code mismatch")
    _require(
        raw.get("provider_foundation") == foundation,
        "raw provider_foundation must match scoring",
    )
    _require(
        raw_provider.get("provider_name") == "eastmoney-fundmobapi",
        "raw holdings provider must be Eastmoney",
    )
    _require(
        raw_provider.get("data_quality") == "fresh",
        "raw holdings data_quality must be fresh",
    )
    _require(
        _eastmoney_source_url(raw_provider.get("source_url")),
        "raw holdings source_url must point to Eastmoney",
    )
    _require_layer(layers, "holdings", "eastmoney-fundmobapi")
    _require_layer(layers, "announcements", "cninfo-announcement")
    _require(
        layers.get("announcements", {}).get("source_url") == CNINFO_ANNOUNCEMENT_QUERY_URL,
        "announcements layer source_url must point to CNINFO",
    )
    _require(
        layers.get("market_quotes", {}).get("provider_name") in REAL_QUOTE_PROVIDERS,
        "market quotes layer must use a real quote provider",
    )
    _require_real_layer(layers.get("market_quotes", {}), "market_quotes")
    _require_layer(layers, "derived_signals", "mixed-derived-signals")

    for layer_name in ("narrative_registry", "stock_mappings", "evidence", "signals"):
        layer = layers.get(layer_name, {})
        _require(
            layer.get("data_quality") == "mock",
            f"{layer_name} layer must remain mock in enriched acceptance",
        )
        _require(layer.get("is_mock") is True, f"{layer_name} layer must be marked mock")
        _require(
            _mock_source_url(layer.get("source_url")),
            f"{layer_name} layer source_url must disclose mock fixture",
        )

    _require(
        announcements.get("version") == "cninfo-announcement-v1",
        "raw announcements version must be cninfo-announcement-v1",
    )
    _require(
        announcements.get("data_quality") == "fresh",
        "raw announcements data_quality must be fresh",
    )
    _require(
        announcements.get("missing_stock_codes") == [],
        "announcements must not miss requested stock codes",
    )
    _require(
        isinstance(announcement_items, list)
        and len(announcement_items) >= min_announcement_count,
        f"announcement count must be at least {min_announcement_count}",
    )
    _require(
        raw_announcement_evidence.get("version") == "announcement-evidence-v1",
        "raw announcement evidence version mismatch",
    )
    _require(
        raw_announcement_evidence.get("data_quality") == "fresh",
        "raw announcement evidence data_quality must be fresh",
    )
    _require(
        isinstance(raw_evidence, list) and len(raw_evidence) >= min_announcement_count,
        f"announcement evidence count must be at least {min_announcement_count}",
    )
    _require(
        raw_announcement_evidence == scoring_announcement_evidence,
        "scoring announcement evidence must match raw announcement evidence",
    )
    _require(
        all(item.get("source") == "cninfo_announcement" for item in raw_evidence),
        "announcement evidence items must come from cninfo_announcement",
    )
    _require(
        all(_cninfo_static_url(item.get("source_url")) for item in raw_evidence),
        "announcement evidence source_url values must point to CNINFO static URLs",
    )
    _require(
        raw_market_quotes.get("version") == "eastmoney-market-quote-v1",
        "market quotes version mismatch",
    )
    _require(
        raw_market_quotes.get("provider_name") in REAL_QUOTE_PROVIDERS,
        "market quotes provider must be a real quote provider",
    )
    _require(
        raw_market_quotes.get("data_quality") == "fresh",
        "market quotes data_quality must be fresh",
    )
    _require(
        raw_market_quotes.get("missing_stock_codes") == [],
        "market quotes must not miss requested stock codes",
    )
    _require(
        isinstance(quotes, list) and len(quotes) >= min_quote_count,
        f"market quote count must be at least {min_quote_count}",
    )
    _require(
        raw_market_quotes == scoring_market_quotes,
        "scoring market quotes must match raw market quotes",
    )
    _require(
        all(_real_quote_source_url(item.get("source_url")) for item in quotes),
        "market quote source_url values must point to real quote providers",
    )
    _require(
        all(item.get("source_provider") in REAL_QUOTE_SOURCE_PROVIDERS for item in quotes),
        "market quote source_provider values must be real quote providers",
    )
    _require(
        raw_derived_signals == scoring_derived_signals,
        "scoring derived signals must match raw derived signals",
    )
    _require(
        isinstance(raw_derived_signals, list),
        "derived_signal_events must be a list",
    )
    _require(
        _has_source(raw_derived_signals, "cninfo_announcement"),
        "derived signals must include cninfo_announcement",
    )
    _require(
        _has_source(raw_derived_signals, "market_quote"),
        "derived signals must include market_quote",
    )
    signal_ids = {
        str(item.get("signal_id"))
        for item in raw.get("signal_events", [])
        if item.get("signal_id")
    }
    _require(
        all(item.get("signal_id") in signal_ids for item in raw_derived_signals),
        "raw signal_events must include all derived signals",
    )
    _require(
        scoring.get("metadata", {}).get("data_quality") == "partial",
        "scoring data_quality must be partial",
    )
    _require(
        foundation.get("effective_data_quality") == "partial",
        "provider foundation effective_data_quality must be partial",
    )
    _require(
        foundation.get("disclosure_required") is True,
        "provider foundation must require disclosure",
    )
    _require(
        _contains_all(
            str(foundation.get("disclosure_message") or ""),
            ("混合数据源", "Eastmoney", "CNINFO", "Market Quotes", "Mock fixtures"),
        ),
        "provider foundation disclosure_message must disclose mixed real and mock data",
    )
    _require(
        raw.get("degradation_events", []) == degradation_events,
        "raw degradation events must match scoring",
    )
    _require(
        foundation.get("degradation_events", []) == degradation_events,
        "provider foundation degradation events must match scoring",
    )
    _require(
        all(_allowed_degradation_event(item) for item in degradation_events),
        "unexpected degradation event",
    )
    if degradation_events:
        _require(
            "降级事件" in str(foundation.get("disclosure_message") or ""),
            "provider foundation must disclose degradation events",
        )
    _require(manifest.get("provider_mode") == "eastmoney", "manifest provider_mode mismatch")
    _require(manifest.get("data_quality") == "partial", "manifest data_quality mismatch")
    _require(manifest.get("provider_foundation") == foundation, "manifest mismatch")
    _require(
        review_queue.get("candidate_review_queue", {}).get("version")
        == "candidate-review-queue-v1",
        "review queue version mismatch",
    )
    expected = (
        "混合数据源",
        "Eastmoney",
        "CNINFO",
        "Market Quotes",
        "Derived Signals",
        "Mock fixtures",
    )
    _require(_contains_all(markdown, expected), "Markdown report disclosure mismatch")
    _require(_contains_all(html, expected), "HTML report disclosure mismatch")


def _require_layer(
    layers: dict[str, Any],
    layer_name: str,
    provider_name: str,
) -> None:
    layer = layers.get(layer_name, {})
    _require(
        layer.get("provider_name") == provider_name,
        f"{layer_name} layer provider mismatch",
    )
    _require(
        layer.get("data_quality") == "fresh",
        f"{layer_name} layer data_quality must be fresh",
    )
    _require(layer.get("is_mock") is False, f"{layer_name} layer must not be mock")


def _require_real_layer(layer: dict[str, Any], layer_name: str) -> None:
    _require(
        layer.get("data_quality") == "fresh",
        f"{layer_name} layer data_quality must be fresh",
    )
    _require(layer.get("is_mock") is False, f"{layer_name} layer must not be mock")


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


def _has_source(items: list[dict[str, Any]], source: str) -> bool:
    return any(item.get("source") == source for item in items)


def _eastmoney_source_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(EASTMONEY_HOLDINGS_URL)


def _cninfo_static_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://static.cninfo.com.cn/")


def _real_quote_source_url(value: Any) -> bool:
    return isinstance(value, str) and (
        value.startswith("https://push2his.eastmoney.com/")
        or value.startswith("https://query1.finance.yahoo.com/")
    )


def _allowed_degradation_event(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    return (
        item.get("type") == "provider_fallback"
        and item.get("provider") == "eastmoney-market-quote"
        and item.get("fallback_provider") == "yahoo-chart"
    )


def _mock_source_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("mock://fixtures/")


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
    print("Real enriched acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print(f"announcement_start_date={announcement_start_date}")
    print(f"min_announcement_count={min_announcement_count}")
    print(f"min_quote_count={min_quote_count}")
    print("holdings=fresh")
    print("announcements=fresh")
    print("market_quotes=fresh")
    print("derived_signals=fresh")
    print("intelligence_layers=mock")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
