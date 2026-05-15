from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_single_fund_demo import DEFAULT_FUND_CODE  # noqa: E402
from src.modules.single_fund_demo import (  # noqa: E402
    SingleFundDemoError,
    validate_single_fund_demo_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate generated single-fund narrative demo artifacts."
    )
    parser.add_argument("--fund-code", default=DEFAULT_FUND_CODE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-mock", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_demo_outputs(
            output_dir=args.output_dir,
            fund_code=args.fund_code,
            require_real=not args.allow_mock,
        )
    except SingleFundDemoError as exc:
        print(f"Single-fund demo validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"single_fund_demo=passed fund_code={args.fund_code}")
    return 0


def validate_demo_outputs(
    output_dir: Path,
    fund_code: str = DEFAULT_FUND_CODE,
    require_real: bool = True,
) -> None:
    demo_json = output_dir / f"fund_{fund_code}_demo.json"
    demo_html = output_dir / f"fund_{fund_code}_demo.html"
    raw_path = output_dir / f"fund_{fund_code}_raw.json"
    scoring_path = output_dir / f"fund_{fund_code}_scoring.json"
    snapshot_path = output_dir / f"fund_{fund_code}_workspace_snapshot.json"
    for path in [demo_json, demo_html, raw_path, scoring_path, snapshot_path]:
        if not path.exists():
            raise SingleFundDemoError(f"missing required artifact: {path.name}")
    payload = _read_json(demo_json)
    validate_single_fund_demo_payload(payload, require_real=require_real)
    if payload["fund"]["fund_code"] != fund_code:
        raise SingleFundDemoError("demo fund code does not match requested fund")
    if payload["primary_narrative"]["name"] != "Premium Baijiu Consumption":
        raise SingleFundDemoError("expected 161725 demo narrative is missing")
    if payload["primary_narrative"]["stage"] not in {
        "emerging",
        "accelerating",
        "mature",
        "weakening",
        "broken",
    }:
        raise SingleFundDemoError("demo narrative stage is not recognized")
    html = demo_html.read_text(encoding="utf-8")
    for marker in [
        "Top Holdings Narrative Map",
        "Premium Baijiu Consumption",
        "Data Sources",
        "Derived Signals",
    ]:
        if marker not in html:
            raise SingleFundDemoError(f"demo html missing marker: {marker}")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SingleFundDemoError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
