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

from src.scanners.collaboration_handoff_bundle import (
    build_collaboration_handoff_bundle,
    render_collaboration_handoff_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local collaboration review handoff bundle.")
    parser.add_argument(
        "--research-export",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "narrative_research_workbench" / "current" / "narrative_research_export_pack.json",
    )
    parser.add_argument(
        "--quality-audit",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "narrative_quality" / "round5_final" / "narrative_quality_audit.json",
    )
    parser.add_argument("--decisions", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "collaboration_handoff" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    decisions = _read_decisions(args.decisions)
    bundle = build_collaboration_handoff_bundle(
        research_export=_read_json(args.research_export),
        quality_audit=_read_json(args.quality_audit),
        requested_decisions=decisions,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "collaboration_handoff_bundle.json"
    html_path = args.output_dir / "collaboration_handoff_bundle.html"
    _write_json(json_path, bundle)
    html_path.write_text(render_collaboration_handoff_html(bundle), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "requested_decision_count": bundle["summary"]["requested_decision_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_decisions(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    payload = _read_json(path)
    decisions = payload.get("requested_decisions")
    return decisions if isinstance(decisions, list) else []


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
