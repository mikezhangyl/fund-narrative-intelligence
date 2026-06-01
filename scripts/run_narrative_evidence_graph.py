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

from src.config import DEFAULT_OUTPUT_DIR
from src.scanners.narrative_evidence_graph import (
    build_narrative_evidence_graph,
    render_narrative_evidence_graph_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a narrative comparison and evidence graph artifact."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "narrative_research_workbench" / "current",
    )
    parser.add_argument("--narrative", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    graph = build_narrative_evidence_graph(
        source_events=_extract_events(payload),
        narratives=args.narrative,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "narrative_evidence_graph.json", graph)
    (args.output_dir / "narrative_evidence_graph.html").write_text(
        render_narrative_evidence_graph_html(graph),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "node_count": graph["summary"]["node_count"],
                "edge_count": graph["summary"]["edge_count"],
                "json": str(args.output_dir / "narrative_evidence_graph.json"),
                "html": str(args.output_dir / "narrative_evidence_graph.html"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _extract_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if isinstance(results, list):
        return [row for row in results if isinstance(row, dict)]
    return []


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
