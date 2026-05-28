from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill V2 Chinese-first fields into narrative registry JSON files."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Registry JSON files to normalize in place.",
    )
    return parser


def migrate_registry_file(path: Path) -> None:
    from src.modules.narrative_intelligence.model import normalize_registry_payload

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    normalized = normalize_registry_payload(payload)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for path in args.paths:
        migrate_registry_file(path.expanduser().resolve(strict=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
