from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REVIEWED_REGISTRY_PATH,
    FIXTURE_DIR,
)
from src.scanners.announcement_mapping_intake import (  # noqa: E402
    build_announcement_mapping_intake_report,
    render_announcement_mapping_intake_html,
)

DEFAULT_EVENTS_PATH = FIXTURE_DIR / "announcement_events_for_mapping_intake.v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run announcement source events into candidate mapping evidence intake."
    )
    parser.add_argument("--events-path", type=Path, default=DEFAULT_EVENTS_PATH)
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REVIEWED_REGISTRY_PATH)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "announcement_mapping_intake",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_announcement_mapping_intake_report(
        event_payload=_read_json(args.events_path),
        registry_payload=_read_json(args.registry_path),
    )
    _write_outputs(output_dir=args.output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "announcement_mapping_intake_report.json"),
                "html": str(args.output_dir / "announcement_mapping_intake_report.html"),
                "status": report["status"],
                "candidate_mapping_count": report["summary"]["candidate_mapping_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "announcement_mapping_intake_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "announcement_mapping_intake_report.html").write_text(
        render_announcement_mapping_intake_html(report),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
