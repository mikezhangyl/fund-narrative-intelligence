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
from src.providers.cninfo import CNInfoAnnouncementProvider  # noqa: E402
from src.scanners.cninfo_disclosure_events import (  # noqa: E402
    build_cninfo_disclosure_event_report,
    render_cninfo_disclosure_event_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch or normalize CNINFO announcement metadata into official disclosure source events."
    )
    parser.add_argument("--stock-code", action="append", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--input-json", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "cninfo_disclosure_events",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    announcements_payload = (
        _read_json(args.input_json)
        if args.input_json
        else CNInfoAnnouncementProvider().get_announcements(
            stock_codes=args.stock_code,
            as_of_date=args.as_of_date,
            start_date=args.start_date,
        )
    )
    report = build_cninfo_disclosure_event_report(
        announcements_payload=announcements_payload
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "cninfo_disclosure_events.json"
    html_path = args.output_dir / "cninfo_disclosure_events.html"
    _write_json(json_path, report)
    html_path.write_text(render_cninfo_disclosure_event_html(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "data_quality": report.get("data_quality"),
                "event_count": report.get("summary", {}).get("event_count", 0),
                "json_path": str(json_path),
                "html_path": str(html_path),
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
