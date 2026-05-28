from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a gateway limit-up/down market-temperature probe."
    )
    parser.add_argument("--trade-date", default="2026-05-22")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or _default_output_dir("limit_up_down_probe")
    output_dir.mkdir(parents=True, exist_ok=True)
    source = ConsolidatedMarketDataSource()
    failures: list[dict[str, str]] = []
    try:
        row = source.fetch_limit_up_down_stats(trade_date=args.trade_date)
    except Exception as exc:
        row = {}
        failures.append({"capability": "limit_up_down_stats", "reason": str(exc)})
    rows = [row] if row else []
    result = _result(
        capability="limit_up_down_stats",
        data_fetch_mode="gateway_provider_neutral",
        rows=rows,
        failures=failures,
        degradation_events=getattr(source, "degradation_events", []),
    )
    report = _report("limit-up-down-probe-v1", result)
    _write_outputs(output_dir, "limit_up_down_report", report)
    print(
        json.dumps(
            _summary(output_dir, "limit_up_down_report", result),
            ensure_ascii=False,
        )
    )
    return 0


def _default_output_dir(name: str) -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / name / timestamp


def _result(
    *,
    capability: str,
    data_fetch_mode: str,
    rows: list[dict[str, Any]],
    failures: list[dict[str, str]],
    degradation_events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "capability": capability,
        "status": _status(rows, failures),
        "data_fetch_mode": data_fetch_mode,
        "provider": _first_value(rows, "provider"),
        "source": _first_value(rows, "source"),
        "row_count": len(rows),
        "rows": rows,
        "failures": failures,
        "degradation_events": degradation_events,
    }


def _status(rows: list[dict[str, Any]], failures: list[dict[str, str]]) -> str:
    if rows and not failures:
        return "completed"
    return "failed" if failures else "missing"


def _report(version: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": version,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "result": result,
    }


def _write_outputs(output_dir: Path, stem: str, report: dict[str, Any]) -> None:
    (output_dir / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.md").write_text(
        _markdown_report(report["result"]),
        encoding="utf-8",
    )


def _markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Limit-Up/Down Probe",
        "",
        f"- Status: `{result['status']}`",
        f"- Data Fetch Mode: `{result['data_fetch_mode']}`",
        f"- Source: `{result['source']}`",
        f"- Rows: `{result['row_count']}`",
        "",
        "## Failures",
        "",
    ]
    lines.extend(_failure_lines(result["failures"]))
    lines.append("")
    return "\n".join(lines)


def _failure_lines(failures: list[dict[str, str]]) -> list[str]:
    if not failures:
        return ["- None"]
    return [f"- `{item['capability']}`: {item['reason']}" for item in failures]


def _summary(output_dir: Path, stem: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "json": str(output_dir / f"{stem}.json"),
        "markdown": str(output_dir / f"{stem}.md"),
        "status": result["status"],
    }


def _first_value(rows: list[dict[str, Any]], field: str) -> str:
    if not rows:
        return ""
    return str(rows[0].get(field) or "")


if __name__ == "__main__":
    raise SystemExit(main())
