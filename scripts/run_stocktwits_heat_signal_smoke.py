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
from src.scanners.stocktwits_heat_signal import (  # noqa: E402
    StocktwitsHeatSignalProvider,
    render_stocktwits_heat_signal_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a controlled Stocktwits heat-signal smoke artifact."
    )
    parser.add_argument("--symbol", action="append", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    parser.add_argument("--cache-ttl-seconds", type=int, default=300)
    parser.add_argument("--input-json", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "stocktwits_heat_signal",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    provider = StocktwitsHeatSignalProvider(
        fetcher=_fixture_fetcher(args.input_json) if args.input_json else None,
        timeout_seconds=args.timeout_seconds,
        cache_ttl_seconds=args.cache_ttl_seconds,
    )
    payload = provider.get_heat_signals(
        symbols=args.symbol,
        limit=args.limit,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "stocktwits_heat_signal.json"
    html_path = args.output_dir / "stocktwits_heat_signal.html"
    _write_json(json_path, payload)
    html_path.write_text(render_stocktwits_heat_signal_html(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "data_quality": payload.get("data_quality"),
                "message_count": payload.get("summary", {}).get("message_count", 0),
                "degradation_count": payload.get("summary", {}).get("degradation_count", 0),
                "json_path": str(json_path),
                "html_path": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _fixture_fetcher(input_json: Path):
    def fetcher(_url: str, _timeout_seconds: int) -> dict[str, Any]:
        return json.loads(input_json.read_text(encoding="utf-8"))

    return fetcher


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
