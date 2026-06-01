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

from src.scanners.replay_alert_review import (
    build_replay_alert_review,
    render_replay_alert_review_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review replay alert usefulness and noise.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "historical_replay" / "current" / "historical_replay_run.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "historical_replay" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    review = build_replay_alert_review(replay_run=_read_json(args.replay))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "replay_alert_review.json"
    html_path = args.output_dir / "replay_alert_review.html"
    _write_json(json_path, review)
    html_path.write_text(render_replay_alert_review_html(review), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "alert_count": review["summary"]["alert_count"],
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
