from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DEFAULT_REVIEWED_REGISTRY_PATH,
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
)
from src.modules.single_fund_demo import (  # noqa: E402
    SingleFundDemoError,
    validate_single_fund_demo_payload,
    write_single_fund_demo_artifacts,
)
from src.modules.workspace_snapshot.builder import (  # noqa: E402
    build_workspace_snapshot,
)
from src.orchestrator import run_pipeline  # noqa: E402

DEFAULT_FUND_CODE = "161725"
DEFAULT_ANNOUNCEMENT_START_DATE = "2026-01-01"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "demo_161725"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a real single-fund narrative demo for the top ten holdings."
    )
    parser.add_argument("--fund-code", default=DEFAULT_FUND_CODE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--announcement-start-date",
        default=DEFAULT_ANNOUNCEMENT_START_DATE,
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
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help=(
            "Deprecated alias for --allow-degraded. Generate the demo even if "
            "provider layers are mock or unavailable."
        ),
    )
    parser.add_argument(
        "--allow-degraded",
        action="store_true",
        help=(
            "Generate the demo when non-core provider layers are mock or unavailable; "
            "the HTML data-source notice must disclose those layers."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = run_demo(
            fund_code=args.fund_code,
            output_dir=args.output_dir,
            announcement_start_date=args.announcement_start_date,
            narrative_registry_path=args.narrative_registry_path,
            stock_mappings_path=args.stock_mappings_path,
            require_real=not (args.allow_mock or args.allow_degraded),
        )
    except SingleFundDemoError as exc:
        print(f"Single-fund demo failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unrecoverable single-fund demo error: {exc}", file=sys.stderr)
        return 1

    print("Generated single-fund demo artifacts:")
    for name, path in sorted(paths.items()):
        print(f"{name}={path}")
    return 0


def run_demo(
    fund_code: str,
    output_dir: Path,
    announcement_start_date: str,
    narrative_registry_path: Path,
    stock_mappings_path: Path,
    require_real: bool = True,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = run_pipeline(
        fund_code=fund_code,
        provider_mode="eastmoney",
        output_dir=output_dir,
        include_announcement_evidence=True,
        announcement_start_date=announcement_start_date,
        include_market_quotes=True,
        include_valuation_snapshots=True,
        valuation_snapshot_source="eastmoney",
        include_financial_metrics=True,
        include_news_evidence=True,
        narrative_registry_mode="reviewed",
        narrative_registry_path=narrative_registry_path,
        stock_mapping_mode="reviewed",
        stock_mappings_path=stock_mappings_path,
        base_intelligence_mode="provider-derived",
    )
    raw = _read_json(artifacts["raw"])
    scoring = _read_json(artifacts["scoring"])
    _require_mapped_narrative(scoring)
    workspace_snapshot_path = build_workspace_snapshot(output_dir)
    workspace_snapshot = _read_json(workspace_snapshot_path)
    demo_paths = write_single_fund_demo_artifacts(
        raw=raw,
        scoring=scoring,
        workspace_snapshot=workspace_snapshot,
        output_dir=output_dir,
    )
    demo_payload = _read_json(demo_paths["demo_json"])
    validate_single_fund_demo_payload(demo_payload, require_real=require_real)
    return {
        **artifacts,
        "workspace_snapshot": workspace_snapshot_path,
        **demo_paths,
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SingleFundDemoError(f"{path} must contain a JSON object")
    return payload


def _require_mapped_narrative(scoring: dict[str, Any]) -> None:
    if scoring.get("primary_narrative"):
        return
    coverage = scoring.get("mapping_coverage") or {}
    unmapped = scoring.get("unmapped_holdings") or []
    sample = ", ".join(
        f"{item.get('stock_code')} {item.get('stock_name')}"
        for item in unmapped[:5]
        if isinstance(item, dict)
    )
    raise SingleFundDemoError(
        "no primary narrative was produced; reviewed stock mappings cover "
        f"{coverage.get('covered_holding_count', 0)} of "
        f"{coverage.get('total_holding_count', 0)} holdings"
        + (f". unmapped sample: {sample}" if sample else "")
    )


if __name__ == "__main__":
    raise SystemExit(main())
