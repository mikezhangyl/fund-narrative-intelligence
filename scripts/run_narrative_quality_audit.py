from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_SRC = PROJECT_ROOT / "services" / "stock-narrative-service" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from stock_narrative_service.config import ServiceConfig  # noqa: E402
from stock_narrative_service.storage import NarrativeStore  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export Narrative Service quality audit artifacts.",
    )
    parser.add_argument(
        "--candidate-events-path",
        type=Path,
        default=ServiceConfig.candidate_events_path,
    )
    parser.add_argument("--intake-ledger-path", type=Path)
    parser.add_argument("--as-of", default="")
    parser.add_argument("--freshness-window-days", default="")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "narrative_quality",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ServiceConfig(
        candidate_events_path=args.candidate_events_path,
        intake_ledger_path=(
            args.intake_ledger_path
            if args.intake_ledger_path
            else args.output_dir / "empty_intake_ledger.json"
        ),
    )
    store = NarrativeStore(config)
    audit = store.quality_audit(
        as_of=args.as_of,
        freshness_window_days=args.freshness_window_days,
    )
    html = store.quality_audit_html(
        as_of=args.as_of,
        freshness_window_days=args.freshness_window_days,
    )
    output_paths = _write_outputs(output_dir=args.output_dir, audit=audit, html=html)
    print(
        json.dumps(
            {
                "status": "completed",
                "json": str(output_paths["json"]),
                "html": str(output_paths["html"]),
                "narrative_count": audit["summary"]["narrative_count"],
                "issue_count": audit["summary"]["issue_count"],
                "formula_version": audit["formula_version"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_outputs(
    *,
    output_dir: Path,
    audit: dict[str, Any],
    html: str,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "narrative_quality_audit.json"
    html_path = output_dir / "narrative_quality_audit.html"
    json_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    html_path.write_text(html, encoding="utf-8")
    return {"json": json_path, "html": html_path}


if __name__ == "__main__":
    raise SystemExit(main())
