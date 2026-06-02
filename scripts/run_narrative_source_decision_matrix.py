from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scanners.narrative_source_decision_matrix import (
    build_narrative_source_decision_matrix,
    render_narrative_source_decision_matrix_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the R13 narrative source decision matrix artifacts."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT
        / "outputs"
        / "narrative_source_decision_matrix"
        / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    matrix = build_narrative_source_decision_matrix()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "narrative_source_decision_matrix.json"
    html_path = args.output_dir / "narrative_source_decision_matrix.html"
    _write_json(json_path, matrix)
    html_path.write_text(
        render_narrative_source_decision_matrix_html(matrix),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "source_group_count": matrix["summary"]["source_group_count"],
                "provider_count": matrix["summary"]["provider_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
