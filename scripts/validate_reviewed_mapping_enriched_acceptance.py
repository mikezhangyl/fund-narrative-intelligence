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
            "--include-valuation-snapshots",
            "--valuation-source",
            "eastmoney",
            "--include-financial-metrics",
            "--include-news-evidence",
            "--output-dir",
            str(output_dir),
        ]
    )
    workspace_snapshot_path = output_dir / f"fund_{fund_code}_workspace_snapshot.json"
    if workspace_snapshot_path.exists():
        workspace_snapshot_path.unlink()
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    _run_cli(["--build-workspace-snapshot", str(output_dir)])
    _run_cli(["--validate-workspace-snapshot", str(workspace_snapshot_path)])
    _validate_reviewed_store_metadata(
        narrative_registry_path=narrative_registry_path,
        stock_mappings_path=stock_mappings_path,
    )
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
        require_news_evidence=True,
    )
    raw = _read_json(output_dir / f"fund_{fund_code}_raw.json")
    scoring = _read_json(output_dir / f"fund_{fund_code}_scoring.json")
    signal_trace = _read_json(output_dir / f"fund_{fund_code}_signal_trace.json")
    markdown = (output_dir / f"fund_{fund_code}_report.md").read_text(encoding="utf-8")
    html = (output_dir / f"fund_{fund_code}_report.html").read_text(encoding="utf-8")
    foundation = scoring.get("provider_foundation", {})
    layers = foundation.get("layers", {})
    registry_layer = layers.get("narrative_registry", {})
    mapping_layer = layers.get("stock_mappings", {})
    valuation_layer = layers.get("valuation", {})
    financial_layer = layers.get("financial_metrics", {})
    mappings = raw.get("stock_narrative_mappings") or []
    coverage = raw.get("mapping_coverage", {})
    valuation_snapshots = raw.get("valuation_snapshots")
    financial_metrics = raw.get("financial_metrics")
    derived_signal_events = raw.get("derived_signal_events") or []
    valuation_signal_events = [
        item
        for item in derived_signal_events
        if item.get("source") == "valuation_snapshot"
    ]

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
    _require_layer_review_metadata(registry_layer, "narrative_registry")
    _require_layer_review_metadata(mapping_layer, "stock_mappings")
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
    _require(
        isinstance(valuation_snapshots, dict) and valuation_snapshots,
        "valuation_snapshots is required",
    )
    _require(
        valuation_snapshots == scoring.get("valuation_snapshots"),
        "raw/scoring valuation_snapshots mismatch",
    )
    _require(
        valuation_snapshots.get("provider_name") == "eastmoney-valuation",
        "valuation_snapshots provider must be eastmoney-valuation",
    )
    _require(
        valuation_snapshots.get("valuation_basis") == "provider_valuation_metrics",
        "valuation_snapshots must use provider_valuation_metrics",
    )
    _require(
        valuation_layer.get("provider_name") == "eastmoney-valuation",
        "valuation layer must use eastmoney-valuation",
    )
    _require(valuation_layer.get("is_mock") is False, "valuation layer must not be mock")
    _require(
        str(valuation_layer.get("source_url") or "").startswith(
            "https://push2.eastmoney.com/api/qt/stock/get"
        )
        or valuation_layer.get("source_url") == "multiple://valuation",
        "valuation layer source_url must disclose Eastmoney valuation source",
    )
    _require(
        isinstance(financial_metrics, dict) and financial_metrics,
        "financial_metrics is required",
    )
    _require(
        financial_metrics == scoring.get("financial_metrics"),
        "raw/scoring financial_metrics mismatch",
    )
    _require(
        financial_metrics.get("provider_name") == "eastmoney-financial-metrics",
        "financial_metrics provider must be eastmoney-financial-metrics",
    )
    _require(
        financial_layer.get("provider_name") == "eastmoney-financial-metrics",
        "financial metrics layer must use eastmoney-financial-metrics",
    )
    _require(
        financial_layer.get("is_mock") is False,
        "financial metrics layer must not be mock",
    )
    _require(
        derived_signal_events == scoring.get("derived_signal_events"),
        "raw/scoring derived_signal_events mismatch",
    )
    _require(
        any(
            item.get("signal_type") in {"valuation_extreme", "valuation_reset"}
            for item in valuation_signal_events
        ),
        "valuation_snapshots must produce valuation-derived signal events",
    )
    _require(
        all(
            item.get("source_provider") == "eastmoney-valuation"
            for item in valuation_signal_events
        ),
        "valuation-derived signal events must disclose eastmoney-valuation",
    )
    _require(
        signal_trace.get("provider_foundation") == foundation,
        "signal trace provider foundation mismatch",
    )
    _require(
        _signal_trace_contains_source(
            signal_trace,
            source="valuation_snapshot",
            source_provider="eastmoney-valuation",
        ),
        "signal trace must include eastmoney valuation-derived signals",
    )
    _require(
        _signal_trace_contains_source(
            signal_trace,
            source="financial_metrics",
            source_provider="eastmoney-financial-metrics",
        ),
        "signal trace must include eastmoney financial-derived signals",
    )
    expected = (
        "reviewed-registry-store",
        "reviewed-mapping-store",
        "provider-derived-evidence",
        "provider-derived-signals",
        "eastmoney-valuation",
        "eastmoney-financial-metrics",
        "Financial Metrics",
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


def _validate_reviewed_store_metadata(
    narrative_registry_path: Path,
    stock_mappings_path: Path,
) -> None:
    registry = _read_json(narrative_registry_path)
    mappings = _read_json(stock_mappings_path)
    _require_review_metadata(registry, "registry.review_metadata")
    _require_review_metadata(mappings, "mappings.review_metadata")
    for index, narrative in enumerate(registry.get("narratives") or []):
        if narrative.get("human_review_status") == "approved":
            _require_review_fields(narrative, f"registry.narratives[{index}]")
    for index, mapping in enumerate(mappings.get("mappings") or []):
        review = mapping.get("review")
        _require(isinstance(review, dict), f"mappings[{index}] must include review")
        _require(review.get("status") == "approved", f"mappings[{index}] must be approved")
        _require_review_fields(review, f"mappings[{index}].review")


def _require_review_metadata(payload: dict[str, Any], context: str) -> None:
    metadata = payload.get("review_metadata")
    _require(isinstance(metadata, dict), f"{context} must be present")
    _require_review_fields(metadata, context)
    _require(
        metadata.get("review_schema_version") == "review-metadata-v1",
        f"{context}.review_schema_version must be review-metadata-v1",
    )
    review_note = metadata.get("review_note")
    _require(
        isinstance(review_note, str) and bool(review_note.strip()),
        f"{context}.review_note must be a non-empty string",
    )


def _require_review_fields(payload: dict[str, Any], context: str) -> None:
    for field in ("reviewed_by", "reviewed_at"):
        value = payload.get(field)
        _require(
            isinstance(value, str) and bool(value.strip()),
            f"{context}.{field} must be a non-empty string",
        )


def _require_layer_review_metadata(layer: dict[str, Any], layer_name: str) -> None:
    metadata = layer.get("review_metadata")
    _require(isinstance(metadata, dict), f"{layer_name} layer must include review_metadata")
    _require_review_metadata({"review_metadata": metadata}, f"{layer_name}.review_metadata")


def _contains_all(value: str, expected_fragments: tuple[str, ...]) -> bool:
    return all(fragment in value for fragment in expected_fragments)


def _signal_trace_contains_source(
    signal_trace: dict[str, Any],
    *,
    source: str,
    source_provider: str,
) -> bool:
    return any(
        signal.get("source") == source
        and signal.get("source_provider") == source_provider
        for narrative in signal_trace.get("narratives", [])
        if isinstance(narrative, dict)
        for dimension in narrative.get("dimensions", [])
        if isinstance(dimension, dict)
        for signal in dimension.get("signals", [])
        if isinstance(signal, dict)
    )


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
    print("valuation=eastmoney")
    print("financial_metrics=eastmoney")
    print("mock_layers=none")
    print("effective_data_quality=partial")
    print(f"workspace_snapshot=fund_{fund_code}_workspace_snapshot.json")


if __name__ == "__main__":
    raise SystemExit(main())
