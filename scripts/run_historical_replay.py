from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scanners.historical_replay_runner import (
    build_historical_replay_run,
    render_historical_replay_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a deterministic historical replay from local FNI artifacts."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "config" / "historical_replay_input.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "historical_replay" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    replay_input = _read_json(args.input)
    artifacts = {
        key: _read_json(_resolve_path(path, args.input.parent))
        for key, path in _artifact_paths(replay_input).items()
    }
    replay = build_historical_replay_run(
        replay_input=replay_input,
        artifacts=artifacts,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "historical_replay_run.json"
    html_path = args.output_dir / "historical_replay_run.html"
    _write_json(json_path, replay)
    html_path.write_text(render_historical_replay_html(replay), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "run_id": replay["run"]["run_id"],
                "source_event_count": replay["summary"]["source_event_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _artifact_paths(replay_input: dict[str, Any]) -> dict[str, str]:
    artifacts = replay_input.get("artifacts")
    return artifacts if isinstance(artifacts, dict) else {}


def _resolve_path(path: Any, base_dir: Path) -> Path:
    resolved = Path(str(path))
    if resolved.is_absolute():
        return resolved
    project_path = PROJECT_ROOT / resolved
    if project_path.exists():
        return project_path
    return base_dir / resolved


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
