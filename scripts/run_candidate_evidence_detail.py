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
from src.modules.narrative_review.source_evidence import (  # noqa: E402
    build_candidate_evidence_detail,
    render_candidate_evidence_detail_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a source-event evidence drill-down for one candidate narrative."
    )
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--source-events", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "candidate_evidence" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    detail = build_candidate_evidence_detail(
        candidate_id=args.candidate_id,
        review_queue=_read_json(args.queue),
        source_payload=_read_json(args.source_events),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.candidate_id}.json"
    html_path = args.output_dir / f"{args.candidate_id}.html"
    _write_json(json_path, detail)
    html_path.write_text(render_candidate_evidence_detail_html(detail), encoding="utf-8")
    print(
        json.dumps(
            {
                "candidate_id": args.candidate_id,
                "source_event_count": detail["summary"]["source_event_count"],
                "missing_event_count": detail["summary"]["missing_event_count"],
                "json": str(json_path),
                "html": str(html_path),
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
