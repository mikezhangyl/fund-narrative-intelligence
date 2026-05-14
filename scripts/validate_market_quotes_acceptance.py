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
from src.providers.eastmoney import EASTMONEY_HOLDINGS_URL  # noqa: E402

DEFAULT_FUND_CODE = "161725"
DEFAULT_MIN_QUOTE_COUNT = 1
REAL_QUOTE_PROVIDERS = {
    "eastmoney-market-quote",
    "yahoo-chart",
    "mixed-market-quote",
}
REAL_QUOTE_SOURCE_PROVIDERS = {"eastmoney", "yahoo-chart"}


class AcceptanceError(RuntimeError):
    """Raised when the market quotes acceptance contract is not satisfied."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for Eastmoney holdings plus real market "
            "quote snapshots."
        )
    )
    parser.add_argument(
        "--fund-code",
        default=DEFAULT_FUND_CODE,
        help=f"Fund code to validate. Defaults to {DEFAULT_FUND_CODE}.",
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
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            _run_acceptance(
                fund_code=args.fund_code,
                min_quote_count=args.min_quote_count,
                output_dir=output_dir,
            )
            _print_success(
                fund_code=args.fund_code,
                min_quote_count=args.min_quote_count,
                output_dir=output_dir,
            )
            return 0

        with tempfile.TemporaryDirectory(prefix="fni-market-quotes-") as tmp:
            output_dir = Path(tmp)
            _run_acceptance(
                fund_code=args.fund_code,
                min_quote_count=args.min_quote_count,
                output_dir=output_dir,
            )
            _print_success(
                fund_code=args.fund_code,
                min_quote_count=args.min_quote_count,
                output_dir=output_dir,
            )
            return 0
    except AcceptanceError as exc:
        print("Market quotes acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    min_quote_count: int,
    output_dir: Path,
) -> None:
    _run_cli(
        [
            "--fund-code",
            fund_code,
            "--provider-mode",
            "eastmoney",
            "--include-market-quotes",
            "--output-dir",
            str(output_dir),
        ]
    )
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    validate_acceptance_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        min_quote_count=min_quote_count,
    )


def validate_acceptance_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
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
    holdings_layer = layers.get("holdings", {})
    market_layer = layers.get("market_quotes", {})
    raw_provider = raw.get("fund", {}).get("provider_metadata", {})
    raw_market_quotes = raw.get("market_quotes", {})
    scoring_market_quotes = scoring.get("market_quotes", {})
    quotes = raw_market_quotes.get("quotes") or []

    _require(
        raw.get("metadata", {}).get("fund_code") == fund_code,
        "raw fund_code mismatch",
    )
    _require(
        raw_provider.get("provider_name") == "eastmoney-fundmobapi",
        "raw fund provider must be Eastmoney",
    )
    _require(
        raw_provider.get("data_quality") == "fresh",
        "raw holdings data_quality must be fresh",
    )
    _require(
        _eastmoney_source_url(raw_provider.get("source_url")),
        "raw holdings source_url must point to Eastmoney",
    )
    _require(
        holdings_layer.get("provider_name") == "eastmoney-fundmobapi",
        "holdings layer must use eastmoney-fundmobapi",
    )
    _require(
        holdings_layer.get("data_quality") == "fresh",
        "holdings layer must be fresh",
    )
    _require(holdings_layer.get("is_mock") is False, "holdings layer must not be mock")

    _require(
        raw_market_quotes.get("version") == "eastmoney-market-quote-v1",
        "market quotes version mismatch",
    )
    _require(
        raw_market_quotes.get("provider_name") in REAL_QUOTE_PROVIDERS,
        "market quotes provider must be a real quote provider",
    )
    _require(
        raw_market_quotes.get("data_quality") in {"fresh", "partial"},
        "market quotes data_quality must be fresh or partial",
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
        market_layer.get("provider_name") in REAL_QUOTE_PROVIDERS,
        "market quotes layer provider must be a real quote provider",
    )
    _require(
        market_layer.get("data_quality") in {"fresh", "partial"},
        "market quotes layer data_quality must be fresh or partial",
    )
    _require(
        market_layer.get("is_mock") is False,
        "market quotes layer must not be mock",
    )

    for layer_name in ("narrative_registry", "stock_mappings", "evidence", "signals"):
        layer = layers.get(layer_name, {})
        _require(
            layer.get("data_quality") == "mock",
            f"{layer_name} layer must remain mock in V1 market quotes acceptance",
        )
        _require(layer.get("is_mock") is True, f"{layer_name} layer must be marked mock")
        _require(
            _mock_source_url(layer.get("source_url")),
            f"{layer_name} layer source_url must disclose mock fixture",
        )

    _require(
        scoring.get("metadata", {}).get("data_quality") == "partial",
        "scoring data_quality must be partial for mixed real and mock layers",
    )
    _require(
        foundation.get("effective_data_quality") == "partial",
        "provider foundation effective_data_quality must be partial",
    )
    _require(
        manifest.get("provider_mode") == "eastmoney",
        "manifest provider_mode must be eastmoney",
    )
    _require(manifest.get("data_quality") == "partial", "manifest data_quality mismatch")
    _require(
        manifest.get("provider_foundation") == foundation,
        "manifest provider_foundation must match scoring",
    )
    queue = review_queue.get("candidate_review_queue", {})
    _require(
        queue.get("version") == "candidate-review-queue-v1",
        "review queue version mismatch",
    )
    _require(
        _contains_all(markdown, ("混合数据源", "Eastmoney", "Market Quotes", "Mock fixtures")),
        "Markdown report must disclose mixed holdings + market quotes + mock data",
    )
    _require(
        _contains_all(html, ("混合数据源", "Eastmoney", "Market Quotes", "Mock fixtures")),
        "HTML report must disclose mixed holdings + market quotes + mock data",
    )


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


def _eastmoney_source_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(EASTMONEY_HOLDINGS_URL)


def _real_quote_source_url(value: Any) -> bool:
    return isinstance(value, str) and (
        value.startswith("https://push2his.eastmoney.com/")
        or value.startswith("https://query1.finance.yahoo.com/")
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
    min_quote_count: int,
    output_dir: Path,
) -> None:
    print("Market quotes acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print(f"min_quote_count={min_quote_count}")
    print("holdings=fresh")
    print("market_quotes=fresh_or_partial")
    print("intelligence_layers=mock")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
