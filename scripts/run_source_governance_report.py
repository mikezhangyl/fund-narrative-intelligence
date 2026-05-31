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
from src.scanners.source_governance import (  # noqa: E402
    evaluate_source_registry,
    render_source_governance_html,
)

OUTPUT_STEM = "source_governance_report"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate narrative source registry governance gates."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_governance" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = json.loads(args.input.read_text(encoding="utf-8"))
    evaluation = evaluate_source_registry(registry)
    write_outputs(args.output_dir, evaluation)
    return 0 if evaluation["summary"]["blocked_count"] == 0 else 1


def write_outputs(output_dir: Path, evaluation: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{OUTPUT_STEM}.json").write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{OUTPUT_STEM}.html").write_text(
        render_source_governance_html(evaluation),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
