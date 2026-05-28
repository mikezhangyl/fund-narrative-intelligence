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
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    PROJECT_ROOT,
)
from src.scanners.narrative_mapping_trust_audit import (  # noqa: E402
    execute_narrative_mapping_trust_audit,
    render_html_report,
)

METHODOLOGY_PATH = PROJECT_ROOT / "docs/product/narrative-mapping-methodology-v0.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit narrative registry and stock mapping trust readiness."
    )
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REVIEWED_REGISTRY_PATH)
    parser.add_argument(
        "--mappings-path",
        type=Path,
        default=DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "narrative_mapping_trust_audit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry_payload = _read_json_object(args.registry_path)
    mapping_payload = _read_json_object(args.mappings_path)
    report = execute_narrative_mapping_trust_audit(
        registry_payload=registry_payload,
        mapping_payload=mapping_payload,
    )
    _write_outputs(output_dir=args.output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "narrative_mapping_trust_audit.json"),
                "html": str(args.output_dir / "narrative_mapping_trust_audit.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "narrative_mapping_trust_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "narrative_mapping_trust_audit.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
