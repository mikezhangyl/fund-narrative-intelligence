from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import validate_provider_routing_acceptance  # noqa: E402
from src import local_env  # noqa: E402

DEFAULT_FUND_CODE = validate_provider_routing_acceptance.DEFAULT_FUND_CODE
DEFAULT_ROUTING_CONFIG_PATH = (
    validate_provider_routing_acceptance.DEFAULT_ROUTING_CONFIG_PATH
)
AcceptanceError = validate_provider_routing_acceptance.AcceptanceError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run provider-routing acceptance that requires Tushare primary success "
            "for valuation snapshots and financial metrics."
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
        if not local_env.get_config_value("TUSHARE_TOKEN"):
            raise AcceptanceError(
                "TUSHARE_TOKEN must be configured for strict Tushare primary acceptance"
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

        with tempfile.TemporaryDirectory(prefix="fni-tushare-primary-") as tmp:
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
        print("Tushare primary acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    provider_routing_config: Path,
    output_dir: Path,
) -> None:
    validate_provider_routing_acceptance._run_cli(  # noqa: SLF001
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
    validate_provider_routing_acceptance._run_cli(  # noqa: SLF001
        ["--validate-artifact-contracts", str(output_dir)]
    )
    validate_provider_routing_acceptance.validate_acceptance_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        require_fallback_layers=(),
        forbid_fallback_layers=("valuation_snapshots", "financial_metrics"),
        expected_final_providers={
            "market_quotes": validate_provider_routing_acceptance.REAL_QUOTE_PROVIDERS,
            "valuation_snapshots": {"tushare-valuation"},
            "financial_metrics": {"tushare-financial-metrics"},
        },
    )


def _print_success(
    *,
    fund_code: str,
    provider_routing_config: Path,
    output_dir: Path,
) -> None:
    print("Tushare primary acceptance passed:")
    print(f"- fund_code: {fund_code}")
    print(f"- provider_routing_config: {provider_routing_config}")
    print(f"- output_dir: {output_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
