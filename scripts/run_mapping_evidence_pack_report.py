from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR, REGISTRY_DIR  # noqa: E402
from src.scanners.mapping_evidence_pack_report import (  # noqa: E402
    build_mapping_evidence_pack_report,
    render_html_report,
)

DEFAULT_EVIDENCE_PATH = REGISTRY_DIR / "mapping_evidence_packs.v0.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render candidate stock-to-narrative mapping evidence packs."
    )
    parser.add_argument("--evidence-path", type=Path, default=DEFAULT_EVIDENCE_PATH)
    parser.add_argument("--symbols", default="")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "mapping_evidence_pack",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    evidence_payload = _read_json_object(args.evidence_path)
    report = build_mapping_evidence_pack_report(
        evidence_payload=evidence_payload,
        symbols=tuple(_parse_csv(args.symbols)),
    )
    _write_outputs(output_dir=args.output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "mapping_evidence_pack_report.json"),
                "html": str(args.output_dir / "mapping_evidence_pack_report.html"),
                "status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mapping_evidence_pack_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "mapping_evidence_pack_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
