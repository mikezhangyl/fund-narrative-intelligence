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
from src.modules.narrative_review.source_queue import (  # noqa: E402
    build_source_candidate_review_queue,
    render_source_candidate_review_queue_html,
)

OUTPUT_STEM = "source_candidate_review_queue"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a review queue for source-derived candidate narratives."
    )
    parser.add_argument("--inbox", type=Path, required=True)
    parser.add_argument("--digest", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_candidate_review_queue" / "current",
    )
    parser.add_argument("--source-kind")
    parser.add_argument("--trust-tier")
    parser.add_argument("--freshness-state")
    parser.add_argument("--market")
    parser.add_argument("--candidate-state")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inbox = _read_json(args.inbox)
    digest = _read_json(args.digest) if args.digest else None
    queue = build_source_candidate_review_queue(
        candidate_inbox=inbox,
        fresh_digest=digest,
        filters=_filters_from_args(args),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{OUTPUT_STEM}.json"
    html_path = args.output_dir / f"{OUTPUT_STEM}.html"
    _write_json(json_path, queue)
    html_path.write_text(render_source_candidate_review_queue_html(queue), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": queue["status"],
                "visible_count": queue["summary"]["visible_count"],
                "json": str(json_path),
                "html": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _filters_from_args(args: argparse.Namespace) -> dict[str, str]:
    return {
        "source_kind": args.source_kind or "",
        "trust_tier": args.trust_tier or "",
        "freshness_state": args.freshness_state or "",
        "market": args.market or "",
        "candidate_state": args.candidate_state or "",
    }


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
