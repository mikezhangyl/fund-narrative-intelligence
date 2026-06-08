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
from src.modules.narrative_review.source_trust_preflight import (  # noqa: E402
    build_source_trust_preflight,
    render_source_trust_preflight_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run read-only trust preflight for one source-derived candidate."
    )
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_trust_preflight" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    preflight = build_source_trust_preflight(
        candidate_id=args.candidate_id,
        review_queue=_read_json(args.queue),
        evidence_detail=_read_json(args.evidence),
        action_ledger=_read_json(args.ledger),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.candidate_id}.json"
    html_path = args.output_dir / f"{args.candidate_id}.html"
    _write_json(json_path, preflight)
    html_path.write_text(render_source_trust_preflight_html(preflight), encoding="utf-8")
    print(
        json.dumps(
            {
                "candidate_id": args.candidate_id,
                "overall_status": preflight["overall_status"],
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
