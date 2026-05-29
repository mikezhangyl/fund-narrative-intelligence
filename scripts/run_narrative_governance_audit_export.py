from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR, DEFAULT_REVIEWED_REGISTRY_PATH  # noqa: E402
from src.scanners.governance_audit import render_html_report  # noqa: E402
from src.scanners.narrative_governance_audit_export import (  # noqa: E402
    build_narrative_governance_audit_export,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export narrative governance audit rows.")
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REVIEWED_REGISTRY_PATH)
    parser.add_argument("--service-ledger-path", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "narrative_governance_audit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    export = build_narrative_governance_audit_export(
        registry_payload=_read_json(args.registry_path),
        service_ledger_payload=_read_json(args.service_ledger_path)
        if args.service_ledger_path
        else None,
    )
    _write_outputs(output_dir=args.output_dir, export=export)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "narrative_governance_audit_export.json"),
                "html": str(args.output_dir / "narrative_governance_audit_export.html"),
                "status": "completed",
                "record_count": export["summary"]["record_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_outputs(*, output_dir: Path, export: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "narrative_governance_audit_export.json").write_text(
        json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "narrative_governance_audit_export.html").write_text(
        render_html_report(export),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
