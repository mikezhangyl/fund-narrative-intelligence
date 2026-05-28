from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.scanners.sector_scanner import execute_sector_scan  # noqa: E402

DEFAULT_ETF_SYMBOLS = ("510300.SH", "159915.SZ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a partial-safe sector rotation scan."
    )
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--etf-symbols", default=",".join(DEFAULT_ETF_SYMBOLS))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_DIR
        / "sector_scan"
        / datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    data_source = ConsolidatedMarketDataSource()
    result = execute_sector_scan(
        data_source=data_source,
        trade_date=args.trade_date,
        etf_symbols=_symbols(args.etf_symbols),
        limit=args.limit,
    ).to_dict()
    result = {
        **result,
        "data_fetch_mode": "gateway_provider_neutral",
        "provider": _first_value(
            [*result["top_sectors"], *result["top_etfs"]],
            "provider",
        ),
        "source": _first_value(
            [*result["top_sectors"], *result["top_etfs"]],
            "source",
        ),
        "degradation_events": list(getattr(data_source, "degradation_events", [])),
    }
    report = {
        "version": "sector-scan-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "result": result,
    }
    (output_dir / "sector_scan_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "sector_scan_report.md").write_text(
        _markdown_report(report),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "json": str(output_dir / "sector_scan_report.json"),
                "markdown": str(output_dir / "sector_scan_report.md"),
                "status": result["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _symbols(text: str) -> list[str]:
    return [symbol.strip() for symbol in text.split(",") if symbol.strip()]


def _markdown_report(report: dict) -> str:
    result = report["result"]
    lines = [
        "# Sector Scan Report",
        "",
        f"- Status: `{result['status']}`",
        f"- Trade Date: `{result['trade_date']}`",
        f"- Data Fetch Mode: `{result.get('data_fetch_mode') or ''}`",
        f"- Source: `{result.get('source') or ''}`",
        f"- Sector Rows: `{result['sector_count']}`",
        f"- ETF Rows: `{result['etf_count']}`",
        "",
        "## Failures",
        "",
    ]
    if result["failures"]:
        lines.extend(
            f"- `{failure['capability']}`: {failure['reason']}"
            for failure in result["failures"]
        )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _first_value(rows: list[dict], field: str) -> str:
    if not rows:
        return ""
    return str(rows[0].get(field) or "")


if __name__ == "__main__":
    raise SystemExit(main())
