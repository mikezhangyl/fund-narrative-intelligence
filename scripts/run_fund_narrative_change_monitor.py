from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR, FIXTURE_DIR  # noqa: E402
from src.scanners.fund_narrative_change_monitor import (  # noqa: E402
    build_fund_narrative_change_report,
    render_html_report,
)

DEFAULT_SNAPSHOTS_PATH = FIXTURE_DIR / "narrative_change_snapshots.v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a fund narrative change monitor report.")
    parser.add_argument("--snapshots-path", type=Path, default=DEFAULT_SNAPSHOTS_PATH)
    parser.add_argument("--previous-snapshot-path", type=Path)
    parser.add_argument("--current-snapshot-path", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "fund_narrative_change_monitor",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    previous, current = _load_snapshots(args)
    report = build_fund_narrative_change_report(
        previous_snapshot=previous,
        current_snapshot=current,
    )
    _write_outputs(output_dir=args.output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "fund_narrative_change_monitor_report.json"),
                "html": str(args.output_dir / "fund_narrative_change_monitor_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _load_snapshots(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    if args.previous_snapshot_path or args.current_snapshot_path:
        if not args.previous_snapshot_path or not args.current_snapshot_path:
            raise SystemExit("--previous-snapshot-path and --current-snapshot-path must be provided together")
        return _read_json(args.previous_snapshot_path), _read_json(args.current_snapshot_path)
    payload = _read_json(args.snapshots_path)
    return _mapping(payload.get("previous_snapshot")), _mapping(payload.get("current_snapshot"))


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "fund_narrative_change_monitor_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "fund_narrative_change_monitor_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
