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
from src.modules.narrative_review.source_operator_workflow import (  # noqa: E402
    build_source_operator_workflow,
    render_source_operator_workflow_html,
)

OUTPUT_STEM = "source_operator_workflow"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a standalone workflow page from daily digest to candidate review."
    )
    parser.add_argument("--digest", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--preflight-index", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_operator_workflow" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workflow = build_source_operator_workflow(
        fresh_digest=_read_json(args.digest),
        review_queue=_read_json(args.queue),
        preflight_index=_read_json(args.preflight_index) if args.preflight_index else {},
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{OUTPUT_STEM}.json"
    html_path = args.output_dir / f"{OUTPUT_STEM}.html"
    _write_json(json_path, workflow)
    html_path.write_text(render_source_operator_workflow_html(workflow), encoding="utf-8")
    print(
        json.dumps(
            {
                "digest_item_count": workflow["summary"]["digest_item_count"],
                "linked_candidate_count": workflow["summary"]["linked_candidate_count"],
                "json": str(json_path),
                "html": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
