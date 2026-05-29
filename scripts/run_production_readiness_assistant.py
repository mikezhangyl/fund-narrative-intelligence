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
from src.scanners.production_readiness_assistant import (  # noqa: E402
    build_production_readiness_assistant,
    render_html_report,
)

DEFAULT_INPUT_PATH = FIXTURE_DIR / "production_readiness_assistant.v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a production readiness and assisted intelligence export."
    )
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--as-of")
    parser.add_argument("--disable-ai", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "production_readiness_assistant",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _read_json(args.input_path)
    report = build_production_readiness_assistant(
        payload=payload,
        as_of=args.as_of,
        ai_enabled=not args.disable_ai,
    )
    _write_outputs(output_dir=args.output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "production_readiness_assistant.json"),
                "html": str(args.output_dir / "production_readiness_assistant.html"),
                "status": "completed",
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "production_readiness_assistant.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "production_readiness_assistant.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
