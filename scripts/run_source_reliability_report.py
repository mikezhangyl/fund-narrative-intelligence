from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.scanners.source_reliability import (  # noqa: E402
    render_source_reliability_html,
    score_source_reliability_inventory,
)

OUTPUT_STEM = "source_reliability_report"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score narrative source reliability.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_reliability" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inventory = json.loads(args.input.read_text(encoding="utf-8"))
    report = score_source_reliability_inventory(inventory)
    write_outputs(args.output_dir, report)
    return 0


def write_outputs(output_dir: Path, report: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{OUTPUT_STEM}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{OUTPUT_STEM}.html").write_text(
        render_source_reliability_html(report),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
