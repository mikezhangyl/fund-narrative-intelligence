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
        description="Run a gateway fund profile and holdings probe."
    )
    parser.add_argument("--fund-code", default="161725")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.fund_code.strip():
        raise SystemExit("--fund-code must be non-empty")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    output_dir = args.output_dir or _default_output_dir("fund_profile_holdings_probe")
    output_dir.mkdir(parents=True, exist_ok=True)
    source = ConsolidatedMarketDataSource()
    failures: list[dict[str, str]] = []
    profile_rows = _fetch_profile(source, fund_code=args.fund_code, failures=failures)
    holding_rows = _fetch_holdings(
        source,
        fund_code=args.fund_code,
        limit=args.limit,
        failures=failures,
    )
    result = _result(
        fund_code=args.fund_code,
        profile_rows=profile_rows,
        holding_rows=holding_rows,
        failures=failures,
        degradation_events=getattr(source, "degradation_events", []),
    )
    report = _report("fund-profile-holdings-probe-v1", result)
    _write_outputs(output_dir, "fund_profile_holdings_report", report)
    print(
        json.dumps(
            _summary(output_dir, "fund_profile_holdings_report", result),
            ensure_ascii=False,
        )
    )
    return 0


def _fetch_profile(
    source: ConsolidatedMarketDataSource,
    *,
    fund_code: str,
    failures: list[dict[str, str]],
) -> list[dict[str, Any]]:
    try:
        return source.fetch_fund_profile(fund_code=fund_code)
    except Exception as exc:
        failures.append({"capability": "fund_profile", "reason": str(exc)})
        return []


def _fetch_holdings(
    source: ConsolidatedMarketDataSource,
    *,
    fund_code: str,
    limit: int,
    failures: list[dict[str, str]],
) -> list[dict[str, Any]]:
    try:
        return source.fetch_fund_holdings(fund_code=fund_code, limit=limit)
    except Exception as exc:
        failures.append({"capability": "fund_holdings", "reason": str(exc)})
        return []


def _default_output_dir(name: str) -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / name / timestamp


def _result(
    *,
    fund_code: str,
    profile_rows: list[dict[str, Any]],
    holding_rows: list[dict[str, Any]],
    failures: list[dict[str, str]],
    degradation_events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "capability": "fund_profile_holdings",
        "status": _status(profile_rows, holding_rows, failures),
        "data_fetch_mode": "gateway_provider_neutral",
        "fund_code": fund_code,
        "profile_source": _first_value(profile_rows, "source"),
        "holdings_source": _first_value(holding_rows, "source"),
        "profile_row_count": len(profile_rows),
        "holding_row_count": len(holding_rows),
        "profile": profile_rows,
        "holdings": holding_rows,
        "failures": failures,
        "degradation_events": degradation_events,
    }


def _status(
    profile_rows: list[dict[str, Any]],
    holding_rows: list[dict[str, Any]],
    failures: list[dict[str, str]],
) -> str:
    if profile_rows and holding_rows and not failures:
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
        "# Fund Profile/Holdings Probe",
        "",
        f"- Status: `{result['status']}`",
        f"- Data Fetch Mode: `{result['data_fetch_mode']}`",
        f"- Fund Code: `{result['fund_code']}`",
        f"- Profile Source: `{result['profile_source']}`",
        f"- Holdings Source: `{result['holdings_source']}`",
        f"- Profile Rows: `{result['profile_row_count']}`",
        f"- Holding Rows: `{result['holding_row_count']}`",
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
        "profile_rows": result["profile_row_count"],
        "holding_rows": result["holding_row_count"],
    }


def _first_value(rows: list[dict[str, Any]], field: str) -> str:
    if not rows:
        return ""
    return str(rows[0].get(field) or "")


if __name__ == "__main__":
    raise SystemExit(main())
