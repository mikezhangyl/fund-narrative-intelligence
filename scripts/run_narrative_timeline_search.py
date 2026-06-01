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

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.scanners.fresh_narrative_digest import extract_source_events_from_probe  # noqa: E402
from src.scanners.narrative_timeline_search import (  # noqa: E402
    build_narrative_timeline_search,
    render_narrative_timeline_search_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a narrative timeline and source-event search artifact."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "narrative_research_workbench" / "current",
    )
    parser.add_argument("--narrative", default="")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--sector", default="")
    parser.add_argument("--concept", default="")
    parser.add_argument("--source-type", default="")
    parser.add_argument("--freshness", default="")
    parser.add_argument("--quality-state", default="")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=50)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    source_events = extract_source_events_from_probe(payload)
    result = build_narrative_timeline_search(
        source_events=source_events,
        query={
            "narrative": args.narrative,
            "ticker": args.ticker,
            "sector": args.sector,
            "concept": args.concept,
            "source_type": args.source_type,
            "freshness": args.freshness,
            "quality_state": args.quality_state,
            "page": args.page,
            "page_size": args.page_size,
        },
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "narrative_timeline_search.json", result)
    (args.output_dir / "narrative_timeline_search.html").write_text(
        render_narrative_timeline_search_html(result),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "matched_event_count": result["summary"]["matched_event_count"],
                "json": str(args.output_dir / "narrative_timeline_search.json"),
                "html": str(args.output_dir / "narrative_timeline_search.html"),
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
