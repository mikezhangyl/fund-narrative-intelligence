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


class AcceptanceError(RuntimeError):
    """Raised when the announcement acceptance contract is not satisfied."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict V1 acceptance for Eastmoney holdings plus CNINFO "
            "announcement evidence."
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
        help=f"Minimum announcement and evidence count. Defaults to {DEFAULT_MIN_ANNOUNCEMENT_COUNT}.",
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
                announcement_start_date=args.announcement_start_date,
                min_announcement_count=args.min_announcement_count,
                output_dir=output_dir,
            )
            _print_success(
                fund_code=args.fund_code,
                announcement_start_date=args.announcement_start_date,
                min_announcement_count=args.min_announcement_count,
                output_dir=output_dir,
            )
            return 0

        with tempfile.TemporaryDirectory(prefix="fni-announcement-acceptance-") as tmp:
            output_dir = Path(tmp)
            _run_acceptance(
                fund_code=args.fund_code,
                announcement_start_date=args.announcement_start_date,
                min_announcement_count=args.min_announcement_count,
                output_dir=output_dir,
            )
            _print_success(
                fund_code=args.fund_code,
                announcement_start_date=args.announcement_start_date,
                min_announcement_count=args.min_announcement_count,
                output_dir=output_dir,
            )
            return 0
    except AcceptanceError as exc:
        print("Announcement acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(
    fund_code: str,
    announcement_start_date: str,
    min_announcement_count: int,
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
            "--output-dir",
            str(output_dir),
        ]
    )
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    validate_acceptance_outputs(
        output_dir=output_dir,
        fund_code=fund_code,
        min_announcement_count=min_announcement_count,
    )


def validate_acceptance_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
    min_announcement_count: int = DEFAULT_MIN_ANNOUNCEMENT_COUNT,
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
    announcements_layer = layers.get("announcements", {})
    derived_signals_layer = layers.get("derived_signals", {})
    raw_provider = raw.get("fund", {}).get("provider_metadata", {})
    announcements = raw.get("announcements", {})
    announcement_items = announcements.get("announcements") or []
    raw_announcement_evidence = raw.get("announcement_evidence", {})
    scoring_announcement_evidence = scoring.get("announcement_evidence", {})
    raw_evidence = raw_announcement_evidence.get("evidence") or []
    raw_derived_signals = raw.get("derived_signal_events") or []
    scoring_derived_signals = scoring.get("derived_signal_events") or []

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
        holdings_layer.get("provider_name") == "eastmoney-fundmobapi",
        "holdings layer must use eastmoney-fundmobapi",
    )
    _require(
        holdings_layer.get("data_quality") == "fresh",
        "holdings layer must be fresh",
    )
    _require(holdings_layer.get("is_mock") is False, "holdings layer must not be mock")

    _require(
        announcements.get("version") == "cninfo-announcement-v1",
        "raw announcements version must be cninfo-announcement-v1",
    )
    _require(
        announcements.get("data_quality") in {"fresh", "partial"},
        "raw announcements data_quality must be fresh or partial",
    )
    _require(
        isinstance(announcement_items, list)
        and len(announcement_items) >= min_announcement_count,
        f"announcement count must be at least {min_announcement_count}",
    )
    _require(
        announcements_layer.get("provider_name") == "cninfo-announcement",
        "announcements layer must use cninfo-announcement",
    )
    _require(
        announcements_layer.get("data_quality") in {"fresh", "partial"},
        "announcements layer must be fresh or partial",
    )
    _require(
        announcements_layer.get("is_mock") is False,
        "announcements layer must not be mock",
    )
    _require(
        announcements_layer.get("source_url") == CNINFO_ANNOUNCEMENT_QUERY_URL,
        "announcements layer source_url must point to CNINFO",
    )

    _require(
        raw_announcement_evidence.get("version") == "announcement-evidence-v1",
        "raw announcement evidence version mismatch",
    )
    _require(
        raw_announcement_evidence.get("data_quality") in {"fresh", "partial"},
        "raw announcement evidence data_quality must be fresh or partial",
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
        isinstance(raw_derived_signals, list)
        and len(raw_derived_signals) >= min_announcement_count,
        f"derived announcement signal count must be at least {min_announcement_count}",
    )
    _require(
        raw_derived_signals == scoring_derived_signals,
        "scoring derived signals must match raw derived signals",
    )
    _require(
        all(item.get("source") == "cninfo_announcement" for item in raw_derived_signals),
        "derived signals must come from cninfo_announcement",
    )
    signal_ids = {
        str(item.get("signal_id"))
        for item in raw.get("signal_events", [])
        if item.get("signal_id")
    }
    _require(
        all(item.get("signal_id") in signal_ids for item in raw_derived_signals),
        "raw signal_events must include derived announcement signals",
    )
    _require(
        derived_signals_layer.get("provider_name") == "cninfo-derived-signals",
        "derived signals layer must use cninfo-derived-signals",
    )
    _require(
        derived_signals_layer.get("data_quality") in {"fresh", "partial"},
        "derived signals layer data_quality must be fresh or partial",
    )
    _require(
        derived_signals_layer.get("is_mock") is False,
        "derived signals layer must not be mock",
    )

    for layer_name in ("narrative_registry", "stock_mappings", "evidence", "signals"):
        layer = layers.get(layer_name, {})
        _require(
            layer.get("data_quality") == "mock",
            f"{layer_name} layer must remain mock in V1 announcement acceptance",
        )
        _require(layer.get("is_mock") is True, f"{layer_name} layer must be marked mock")
        _require(
            _mock_source_url(layer.get("source_url")),
            f"{layer_name} layer source_url must disclose mock fixture",
        )

    degradation_events = scoring.get("degradation_events", [])
    _require(
        degradation_events == [],
        "announcement acceptance is strict and must not record degradation events",
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
        _contains_all(markdown, ("混合数据源", "Eastmoney", "CNINFO", "Mock fixtures")),
        "Markdown report must disclose mixed Eastmoney + CNINFO + Mock fixture data",
    )
    _require(
        _contains_all(html, ("混合数据源", "Eastmoney", "CNINFO", "Mock fixtures")),
        "HTML report must disclose mixed Eastmoney + CNINFO + Mock fixture data",
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


def _cninfo_static_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://static.cninfo.com.cn/")


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
    output_dir: Path,
) -> None:
    print("Announcement acceptance passed:")
    print(output_dir)
    print(f"fund_code={fund_code}")
    print("provider_mode=eastmoney")
    print(f"announcement_start_date={announcement_start_date}")
    print(f"min_announcement_count={min_announcement_count}")
    print("holdings=fresh")
    print("announcements=fresh_or_partial")
    print("derived_signals=fresh_or_partial")
    print("intelligence_layers=mock")
    print("effective_data_quality=partial")


if __name__ == "__main__":
    raise SystemExit(main())
