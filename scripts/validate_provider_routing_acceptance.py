# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from contextlib import ExitStack, contextmanager
from functools import partial
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import main as pipeline_main  # noqa: E402
from src.providers import routing as provider_routing  # noqa: E402
from src.providers import (
    tushare_financials as tushare_financials_provider,  # noqa: E402
)
from src.providers import tushare_valuation as tushare_valuation_provider  # noqa: E402
from src.providers.akshare_market import AkshareMarketDataProvider  # noqa: E402
from src.providers.eastmoney import EASTMONEY_HOLDINGS_URL  # noqa: E402

DEFAULT_FUND_CODE = "161725"
DEFAULT_ROUTING_CONFIG_PATH = (
    PROJECT_ROOT / "data" / "provider_routing" / "akshare_tushare.primary-fallback.json"
)
DEFAULT_REQUIRE_FALLBACK_LAYERS = (
    "market_quotes",
    "valuation_snapshots",
    "financial_metrics",
)
REAL_QUOTE_PROVIDERS = {
    "akshare-market-quote",
    "eastmoney-market-quote",
    "yahoo-chart",
    "mixed-market-quote",
}


class AcceptanceError(RuntimeError):
    """Raised when the provider routing acceptance contract is not satisfied."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run provider-routing acceptance for Eastmoney holdings plus routed "
            "market quotes, valuation snapshots, and financial metrics."
        )
    )
    parser.add_argument(
        "--fund-code",
        default=DEFAULT_FUND_CODE,
        help=f"Fund code to validate. Defaults to {DEFAULT_FUND_CODE}.",
    )
    parser.add_argument(
        "--provider-routing-config",
        type=Path,
        default=DEFAULT_ROUTING_CONFIG_PATH,
        help=(
            "Provider routing config JSON. Defaults to the repo sample "
            f"{DEFAULT_ROUTING_CONFIG_PATH}."
        ),
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. If omitted, a temporary directory is used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if not args.provider_routing_config.is_file():
            raise AcceptanceError(
                f"provider routing config does not exist: {args.provider_routing_config}"
            )

        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            _run_acceptance(
                fund_code=args.fund_code,
                provider_routing_config=args.provider_routing_config,
                output_dir=output_dir,
            )
            _print_success(
                fund_code=args.fund_code,
                provider_routing_config=args.provider_routing_config,
                output_dir=output_dir,
            )
            return 0

        with tempfile.TemporaryDirectory(prefix="fni-provider-routing-") as tmp:
            output_dir = Path(tmp)
            _run_acceptance(
                fund_code=args.fund_code,
                provider_routing_config=args.provider_routing_config,
                output_dir=output_dir,
            )
            _print_success(
                fund_code=args.fund_code,
                provider_routing_config=args.provider_routing_config,
                output_dir=output_dir,
            )
            return 0
    except AcceptanceError as exc:
        print("Provider routing acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    provider_routing_config: Path,
    output_dir: Path,
) -> None:
    with _forced_primary_unavailable_context():
        _run_cli(
            [
                "--fund-code",
                fund_code,
                "--provider-mode",
                "eastmoney",
                "--include-market-quotes",
                "--include-valuation-snapshots",
                "--valuation-source",
                "provider",
                "--include-financial-metrics",
                "--provider-routing-config",
                str(provider_routing_config),
                "--output-dir",
                str(output_dir),
            ]
        )
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    validate_acceptance_outputs(output_dir=output_dir, fund_code=fund_code)


@contextmanager
def _forced_primary_unavailable_context():
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                provider_routing,
                "AkshareMarketDataProvider",
                partial(AkshareMarketDataProvider, client_loader=lambda: None),
            )
        )
        stack.enter_context(
            patch.object(
                provider_routing,
                "TushareValuationProvider",
                partial(tushare_valuation_provider.TushareValuationProvider, token=""),
            )
        )
        stack.enter_context(
            patch.object(
                provider_routing,
                "TushareFinancialMetricsProvider",
                partial(
                    tushare_financials_provider.TushareFinancialMetricsProvider,
                    token="",
                ),
            )
        )
        yield


def validate_acceptance_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
    require_fallback_layers: tuple[str, ...] = DEFAULT_REQUIRE_FALLBACK_LAYERS,
    forbid_fallback_layers: tuple[str, ...] = (),
    forbid_provider_unavailable: tuple[str, ...] = (),
    expected_final_providers: dict[str, set[str]] | None = None,
) -> None:
    artifacts = {
        "raw": output_dir / f"fund_{fund_code}_raw.json",
        "scoring": output_dir / f"fund_{fund_code}_scoring.json",
        "review_queue": output_dir / f"fund_{fund_code}_review_queue.json",
        "source_table": output_dir / f"fund_{fund_code}_source_table.json",
        "signal_trace": output_dir / f"fund_{fund_code}_signal_trace.json",
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
    source_table = _read_json(artifacts["source_table"])
    signal_trace = _read_json(artifacts["signal_trace"])
    markdown = artifacts["markdown"].read_text(encoding="utf-8")
    html = artifacts["html"].read_text(encoding="utf-8")

    expected_final_providers = expected_final_providers or {
        "market_quotes": REAL_QUOTE_PROVIDERS,
        "valuation_snapshots": {"eastmoney-valuation"},
        "financial_metrics": {"eastmoney-financial-metrics"},
    }

    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    degradation_events = scoring.get("degradation_events") or []
    raw_provider = raw.get("fund", {}).get("provider_metadata", {})

    _require(raw.get("metadata", {}).get("fund_code") == fund_code, "raw fund_code mismatch")
    _require(
        raw.get("provider_foundation") == foundation,
        "raw provider_foundation must match scoring",
    )
    _require(
        manifest.get("provider_foundation") == foundation,
        "manifest provider_foundation must match scoring",
    )
    _require(
        source_table.get("provider_foundation") == foundation,
        "source_table provider_foundation must match scoring",
    )
    _require(
        signal_trace.get("provider_foundation") == foundation,
        "signal_trace provider_foundation must match scoring",
    )
    _require(
        review_queue.get("provider_foundation") == foundation,
        "review_queue provider_foundation must match scoring",
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

    holdings_layer = layers.get("holdings", {})
    _require(
        holdings_layer.get("provider_name") == "eastmoney-fundmobapi",
        "holdings layer must use eastmoney-fundmobapi",
    )
    _require(
        holdings_layer.get("data_quality") == "fresh",
        "holdings layer must be fresh",
    )
    _require(holdings_layer.get("is_mock") is False, "holdings layer must not be mock")

    market_quotes = raw.get("market_quotes", {})
    valuation_snapshots = raw.get("valuation_snapshots", {})
    financial_metrics = raw.get("financial_metrics", {})
    _require(market_quotes == scoring.get("market_quotes"), "raw/scoring market_quotes mismatch")
    _require(
        valuation_snapshots == scoring.get("valuation_snapshots"),
        "raw/scoring valuation_snapshots mismatch",
    )
    _require(
        financial_metrics == scoring.get("financial_metrics"),
        "raw/scoring financial_metrics mismatch",
    )
    _require_layer_provider(
        layer_name="market_quotes",
        payload=market_quotes,
        layer=layers.get("market_quotes", {}),
        allowed_providers=expected_final_providers["market_quotes"],
    )
    _require_layer_provider(
        layer_name="valuation_snapshots",
        payload=valuation_snapshots,
        layer=layers.get("valuation", {}),
        allowed_providers=expected_final_providers["valuation_snapshots"],
    )
    _require_layer_provider(
        layer_name="financial_metrics",
        payload=financial_metrics,
        layer=layers.get("financial_metrics", {}),
        allowed_providers=expected_final_providers["financial_metrics"],
    )
    _require(
        market_quotes.get("data_quality") in {"fresh", "partial"},
        "market_quotes data_quality must be fresh or partial",
    )
    _require(
        valuation_snapshots.get("data_quality") in {"fresh", "partial"},
        "valuation_snapshots data_quality must be fresh or partial",
    )
    _require(
        financial_metrics.get("data_quality") in {"fresh", "partial"},
        "financial_metrics data_quality must be fresh or partial",
    )
    _require(
        market_quotes.get("quotes"),
        "market_quotes must include at least one quote row",
    )
    _require(
        valuation_snapshots.get("valuations"),
        "valuation_snapshots must include at least one valuation row",
    )
    _require(
        financial_metrics.get("metrics"),
        "financial_metrics must include at least one metric row",
    )

    derived_signals = raw.get("derived_signal_events") or []
    _require(
        isinstance(derived_signals, list) and derived_signals,
        "derived_signal_events must be present",
    )
    derived_sources = {str(item.get("source") or "") for item in derived_signals}
    _require(
        {"market_quote", "valuation_snapshot", "financial_metrics"} <= derived_sources,
        "derived signals must include market_quote, valuation_snapshot, and financial_metrics",
    )

    for layer in require_fallback_layers:
        _require(
            any(
                event.get("type") == "provider_fallback"
                and event.get("layer") == layer
                for event in degradation_events
            ),
            f"missing required provider fallback event for {layer}",
        )
    for layer in forbid_fallback_layers:
        _require(
            not any(
                event.get("type") == "provider_fallback"
                and event.get("layer") == layer
                for event in degradation_events
            ),
            f"unexpected provider fallback event for {layer}",
        )
    for provider_name in forbid_provider_unavailable:
        _require(
            not any(
                event.get("type") == "provider_unavailable"
                and event.get("provider") == provider_name
                for event in degradation_events
            ),
            f"unexpected provider_unavailable event for {provider_name}",
        )

    _require(
        "Data Source Notice" in markdown and "Data Source Notice" in html,
        "report outputs must disclose data source notice",
    )
    _require(
        "provider" in str(raw.get("degradation_events", [])).lower()
        or "provider" in str(degradation_events).lower(),
        "degradation_events must mention provider routing activity",
    )


def _require_layer_provider(
    *,
    layer_name: str,
    payload: dict,
    layer: dict,
    allowed_providers: set[str],
) -> None:
    provider_name = str(payload.get("provider_name") or "")
    _require(
        provider_name in allowed_providers,
        f"{layer_name} provider_name must be one of {sorted(allowed_providers)}",
    )
    _require(
        layer.get("provider_name") == provider_name,
        f"{layer_name} layer provider_name must match payload",
    )
    _require(
        layer.get("is_mock") is False,
        f"{layer_name} layer must not be mock",
    )


def _run_cli(args: list[str]) -> None:
    exit_code = pipeline_main.main(args)
    if exit_code != 0:
        raise AcceptanceError(f"pipeline command failed ({exit_code}): {' '.join(args)}")


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AcceptanceError(f"{path} must contain a JSON object")
    return payload


def _eastmoney_source_url(source_url: object) -> bool:
    return isinstance(source_url, str) and source_url.startswith(EASTMONEY_HOLDINGS_URL)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def _print_success(
    *,
    fund_code: str,
    provider_routing_config: Path,
    output_dir: Path,
) -> None:
    print("Provider routing acceptance passed:")
    print(f"- fund_code: {fund_code}")
    print(f"- provider_routing_config: {provider_routing_config}")
    print(f"- output_dir: {output_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
