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
from src.modules.narrative_review.source_action_ledger import (  # noqa: E402
    append_candidate_review_action,
    build_empty_review_action_ledger,
    render_review_action_ledger_html,
)

OUTPUT_STEM = "source_review_action_ledger"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a source-candidate review action and write a ledger summary."
    )
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument(
        "--action",
        required=True,
        choices=[
            "watch",
            "needs_more_evidence",
            "reject",
            "defer",
            "ready_for_trust_preflight",
        ],
    )
    parser.add_argument("--reason", required=True)
    parser.add_argument("--actor", default="reviewer-placeholder")
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--created-at")
    parser.add_argument("--queue-ref")
    parser.add_argument("--evidence-ref")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_review_action_ledger" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ledger = _read_json(args.ledger) if args.ledger.exists() else build_empty_review_action_ledger()
    queue = _read_json(args.queue)
    updated = append_candidate_review_action(
        ledger=ledger,
        review_queue=queue,
        action_request={
            "candidate_id": args.candidate_id,
            "action": args.action,
            "reason": args.reason,
            "actor": args.actor,
            "idempotency_key": args.idempotency_key,
            "created_at": args.created_at or "",
            "source_artifact_refs": _source_artifact_refs(args),
        },
    )
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    _write_json(args.ledger, updated)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{OUTPUT_STEM}.json"
    html_path = args.output_dir / f"{OUTPUT_STEM}.html"
    _write_json(json_path, updated)
    html_path.write_text(render_review_action_ledger_html(updated), encoding="utf-8")
    print(
        json.dumps(
            {
                "total_action_count": updated["summary"]["total_action_count"],
                "idempotent_replay_count": updated["summary"]["idempotent_replay_count"],
                "json": str(json_path),
                "html": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _source_artifact_refs(args: argparse.Namespace) -> dict[str, str]:
    refs = {"queue": args.queue_ref or str(args.queue)}
    if args.evidence_ref:
        refs["evidence_detail"] = args.evidence_ref
    return refs


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
