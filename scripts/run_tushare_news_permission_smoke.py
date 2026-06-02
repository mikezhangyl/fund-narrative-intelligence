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

from src.market_data.source_layer import ConsolidatedMarketDataSource
from src.scanners.tushare_news_permission_smoke import (
    build_tushare_news_permission_smoke,
    render_tushare_news_permission_smoke_html,
)


DEFAULT_SRC_VALUES = ("sina", "wallstreetcn", "10jqka", "eastmoney", "yicai", "cls")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Tushare news permission feasibility smoke and write JSON/Chinese HTML."
    )
    parser.add_argument("--source-provider", default="tushare")
    parser.add_argument("--src", action="append", dest="src_values")
    parser.add_argument("--start-datetime", required=True)
    parser.add_argument("--end-datetime", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "tushare_news_permission_smoke" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    src_values = args.src_values or list(DEFAULT_SRC_VALUES)
    source = ConsolidatedMarketDataSource()
    report = build_tushare_news_permission_smoke(
        source=source,
        source_provider=args.source_provider,
        src_values=src_values,
        start_datetime=args.start_datetime,
        end_datetime=args.end_datetime,
        limit=args.limit,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "tushare_news_permission_smoke.json"
    html_path = args.output_dir / "tushare_news_permission_smoke.html"
    _write_json(json_path, report)
    html_path.write_text(render_tushare_news_permission_smoke_html(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "json_path": str(json_path),
                "html_path": str(html_path),
                "dev_ready_count": report["summary"]["dev_ready_count"],
                "paid_permission_required_count": report["summary"][
                    "paid_permission_required_count"
                ],
                "blocked_count": report["summary"]["blocked_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
