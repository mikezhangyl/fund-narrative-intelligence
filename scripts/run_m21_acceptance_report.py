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
from src.scanners.m21_acceptance_report import (  # noqa: E402
    build_m21_acceptance_report,
    render_m21_acceptance_report_html,
)

OUTPUT_STEM = "m21_acceptance_report"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the M21 source-derived candidate acceptance report."
    )
    parser.add_argument("--live-probe", type=Path, required=True)
    parser.add_argument("--fixture-probe", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--verification-command", action="append", default=[])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "m21_acceptance" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_m21_acceptance_report(
        artifacts={
            "live_probe": _artifact(args.live_probe),
            "fixture_probe": _artifact(args.fixture_probe),
            "queue": _artifact(args.queue),
            "evidence": _artifact(args.evidence),
            "ledger": _artifact(args.ledger),
            "preflight": _artifact(args.preflight),
            "workflow": _artifact(args.workflow),
        },
        verification_commands=list(args.verification_command),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{OUTPUT_STEM}.json"
    html_path = args.output_dir / f"{OUTPUT_STEM}.html"
    _write_json(json_path, report)
    html_path.write_text(render_m21_acceptance_report_html(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "pm_architect_decision": report["decision"]["pm_architect_decision"],
                "json": str(json_path),
                "html": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _artifact(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "payload": _read_json(path),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
