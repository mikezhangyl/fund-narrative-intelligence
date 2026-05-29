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
from src.scanners.reviewable_fund_report_pack import (  # noqa: E402
    build_reviewable_fund_report_pack,
    render_html_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a static reviewable fund report pack.")
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--reference-artifact",
        action="append",
        default=[],
        help="Optional key=relative/path reference, e.g. narrative_matrix=matrix.html.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "reviewable_fund_report_pack",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pack = build_reviewable_fund_report_pack(
        artifact_root=args.artifact_root,
        reference_artifacts=_parse_reference_artifacts(args.reference_artifact),
    )
    _write_outputs(output_dir=args.output_dir, pack=pack)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "reviewable_fund_report_pack.json"),
                "html": str(args.output_dir / "reviewable_fund_report_pack.html"),
                "status": pack["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_outputs(*, output_dir: Path, pack: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reviewable_fund_report_pack.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "reviewable_fund_report_pack.html").write_text(
        render_html_report(pack),
        encoding="utf-8",
    )


def _parse_reference_artifacts(values: list[str]) -> dict[str, str]:
    refs = {}
    for value in values:
        if "=" not in value:
            raise SystemExit("--reference-artifact must use key=path")
        key, path = value.split("=", 1)
        key = key.strip()
        path = path.strip()
        if not key or not path:
            raise SystemExit("--reference-artifact must use key=path")
        refs[key] = path
    return refs


if __name__ == "__main__":
    raise SystemExit(main())
