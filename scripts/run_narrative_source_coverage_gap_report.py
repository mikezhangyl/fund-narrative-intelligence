from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.scanners.narrative_source_coverage_gap import (  # noqa: E402
    build_narrative_source_coverage_gap_report,
    render_narrative_source_coverage_gap_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a Gateway narrative source coverage gap report for backlog planning."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "narrative_source_coverage_gap" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _read_json(args.input)
    report = build_narrative_source_coverage_gap_report(gateway_probe=payload)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "narrative_source_coverage_gap.json", report)
    _write_text(
        args.output_dir / "narrative_source_coverage_gap.html",
        render_narrative_source_coverage_gap_html(report),
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "missing_count": report["summary"]["missing_count"],
                "degraded_count": report["summary"]["degraded_count"],
                "json": str(args.output_dir / "narrative_source_coverage_gap.json"),
                "html": str(args.output_dir / "narrative_source_coverage_gap.html"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
