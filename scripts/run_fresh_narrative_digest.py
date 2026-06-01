from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scanners.fresh_narrative_digest import (  # noqa: E402
    build_fresh_narrative_digest,
    extract_source_events_from_probe,
    render_fresh_narrative_digest_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a fresh narrative digest from gateway source-event probe output."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _read_json(args.input)
    events = extract_source_events_from_probe(payload)
    digest = build_fresh_narrative_digest(
        source_events=events,
        window_start=args.window_start,
        window_end=args.window_end,
        fixture_mode=bool(payload.get("fixture_mode", True)),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "fresh_narrative_digest.json", digest)
    _write_text(
        args.output_dir / "fresh_narrative_digest.html",
        render_fresh_narrative_digest_html(digest),
    )
    print(
        json.dumps(
            {
                "status": digest["status"],
                "digest_item_count": digest["summary"]["digest_item_count"],
                "json": str(args.output_dir / "fresh_narrative_digest.json"),
                "html": str(args.output_dir / "fresh_narrative_digest.html"),
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
