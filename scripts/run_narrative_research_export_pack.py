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

from src.scanners.narrative_research_export_pack import (
    build_narrative_research_export_pack,
    render_narrative_research_export_pack_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a cited narrative research export pack from local workbench artifacts."
    )
    parser.add_argument(
        "--timeline",
        type=Path,
        default=PROJECT_ROOT
        / "outputs"
        / "narrative_research_workbench"
        / "current"
        / "narrative_timeline_search.json",
    )
    parser.add_argument(
        "--evidence-graph",
        type=Path,
        default=PROJECT_ROOT
        / "outputs"
        / "narrative_research_workbench"
        / "current"
        / "narrative_evidence_graph.json",
    )
    parser.add_argument("--notes", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "narrative_research_workbench" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    timeline = _read_json(args.timeline)
    evidence_graph = _read_json(args.evidence_graph)
    analyst_notes = _read_notes(args.notes)
    pack = build_narrative_research_export_pack(
        timeline_search=timeline,
        evidence_graph=evidence_graph,
        analyst_notes=analyst_notes,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "narrative_research_export_pack.json"
    html_path = args.output_dir / "narrative_research_export_pack.html"
    _write_json(json_path, pack)
    html_path.write_text(render_narrative_research_export_pack_html(pack), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "note_count": pack["summary"]["note_count"],
                "citation_count": pack["summary"]["citation_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_notes(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    payload = _read_json(path)
    notes = payload.get("notes")
    return notes if isinstance(notes, list) else []


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
