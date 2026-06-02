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

from src.scanners.operator_release_readiness import (
    build_operator_release_readiness,
    render_operator_release_readiness_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build operator release readiness notes and runbook index.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "config" / "operator_release_readiness_input.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs" / "operator_release_readiness" / "current")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    readiness = build_operator_release_readiness(release_metadata=_read_json(args.input))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "operator_release_readiness.json"
    html_path = args.output_dir / "operator_release_readiness.html"
    _write_json(json_path, readiness)
    html_path.write_text(render_operator_release_readiness_html(readiness), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "support_runbook_count": readiness["summary"]["support_runbook_count"],
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


if __name__ == "__main__":
    raise SystemExit(main())
