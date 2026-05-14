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


class AcceptanceError(RuntimeError):
    """Raised when the real holdings acceptance contract is not satisfied."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the strict V1 real-holdings acceptance flow through Eastmoney."
        )
    )
    parser.add_argument(
        "--fund-code",
        default=DEFAULT_FUND_CODE,
        help=f"Fund code to validate. Defaults to {DEFAULT_FUND_CODE}.",
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
            _run_acceptance(fund_code=args.fund_code, output_dir=output_dir)
            _print_success(fund_code=args.fund_code, output_dir=output_dir)
            return 0

        with tempfile.TemporaryDirectory(prefix="fni-real-holdings-") as tmp:
            output_dir = Path(tmp)
            _run_acceptance(fund_code=args.fund_code, output_dir=output_dir)
            _print_success(fund_code=args.fund_code, output_dir=output_dir)
            return 0
    except AcceptanceError as exc:
        print("Real holdings acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(fund_code: str, output_dir: Path) -> None:
    _run_cli(
        [
            "--fund-code",
            fund_code,
            "--provider-mode",
            "eastmoney",
            "--output-dir",
            str(output_dir),
        ]
    )
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    validate_acceptance_outputs(output_dir=output_dir, fund_code=fund_code)


def validate_acceptance_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
) -> None:
    artifacts = {
        "raw": output_dir / f"fund_{fund_code}_raw.json",
        "scoring": output_dir / f"fund_{fund_code}_scoring.json",
        "review_queue": output_dir / f"fund_{fund_code}_review_queue.json",
        "source_table": output_dir / f"fund_{fund_code}_source_table.json",
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
    markdown = artifacts["markdown"].read_text(encoding="utf-8")
    html = artifacts["html"].read_text(encoding="utf-8")

    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    holdings_layer = layers.get("holdings", {})
    raw_provider = raw.get("fund", {}).get("provider_metadata", {})

    _require(raw.get("metadata", {}).get("fund_code") == fund_code, "raw fund_code mismatch")
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
        scoring.get("metadata", {}).get("data_quality") == "partial",
        "scoring data_quality must be partial for Eastmoney holdings plus mock intelligence",
    )
    _require(
        foundation.get("effective_data_quality") == "partial",
        "provider foundation effective_data_quality must be partial",
    )
    _require(
        holdings_layer.get("provider_name") == "eastmoney-fundmobapi",
        "Eastmoney holdings layer must use eastmoney-fundmobapi",
    )
    _require(
        holdings_layer.get("data_quality") == "fresh",
        "Eastmoney holdings layer must be fresh",
    )
    _require(
        holdings_layer.get("is_mock") is False,
        "Eastmoney holdings layer must not be mock",
    )
    _require(
        _eastmoney_source_url(holdings_layer.get("source_url")),
        "Eastmoney holdings layer source_url must point to Eastmoney",
    )

    for layer_name in ("narrative_registry", "stock_mappings", "evidence", "signals"):
        layer = layers.get(layer_name, {})
        _require(
            layer.get("data_quality") == "mock",
            f"{layer_name} layer must remain mock in V1 real-holdings acceptance",
        )
        _require(layer.get("is_mock") is True, f"{layer_name} layer must be marked mock")
        _require(
            _mock_source_url(layer.get("source_url")),
            f"{layer_name} layer source_url must disclose mock fixture",
        )

    degradation_events = scoring.get("degradation_events", [])
    _require(
        degradation_events == [],
        "real holdings acceptance is strict and must not fall back to mock",
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
    _require(source_table.get("fund_code") == fund_code, "source table fund_code mismatch")
    _require(
        source_table.get("provider_foundation") == foundation,
        "source table provider_foundation must match scoring",
    )
    queue = review_queue.get("candidate_review_queue", {})
    _require(
        queue.get("version") == "candidate-review-queue-v1",
        "review queue version mismatch",
    )
    _require(
        "混合数据源" in markdown and "Eastmoney" in markdown and "Mock fixtures" in markdown,
        "Markdown report must disclose mixed Eastmoney + Mock fixture data",
    )
    _require(
        "混合数据源" in html and "Eastmoney" in html and "Mock fixtures" in html,
        "HTML report must disclose mixed Eastmoney + Mock fixture data",
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


def _mock_source_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("mock://fixtures/")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def _print_success(fund_code: str, output_dir: Path) -> None:
    print("Real holdings acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print("holdings=fresh")
    print("intelligence_layers=mock")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
