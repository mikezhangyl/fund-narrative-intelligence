from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import DEFAULT_OUTPUT_DIR


def default_output_dir(name: str) -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / name / timestamp


def build_result(
    *,
    capability: str,
    data_fetch_mode: str,
    rows: list[dict[str, Any]],
    failures: list[dict[str, str]],
    degradation_events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "capability": capability,
        "status": status(rows, failures),
        "data_fetch_mode": data_fetch_mode,
        "provider": first_value(rows, "provider"),
        "source": first_value(rows, "source"),
        "row_count": len(rows),
        "rows": rows,
        "failures": failures,
        "degradation_events": degradation_events,
    }


def status(rows: list[dict[str, Any]], failures: list[dict[str, str]]) -> str:
    if rows and not failures:
        return "completed"
    return "failed" if failures else "missing"


def report(version: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": version,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "result": result,
    }


def write_outputs(
    output_dir: Path,
    stem: str,
    title: str,
    payload: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.md").write_text(
        markdown_report(title, payload["result"]),
        encoding="utf-8",
    )


def markdown_report(title: str, result: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Status: `{result['status']}`",
        f"- Data Fetch Mode: `{result['data_fetch_mode']}`",
        f"- Source: `{result['source']}`",
        f"- Rows: `{result['row_count']}`",
        "",
        "## Failures",
        "",
    ]
    lines.extend(failure_lines(result["failures"]))
    lines.append("")
    return "\n".join(lines)


def failure_lines(failures: list[dict[str, str]]) -> list[str]:
    if not failures:
        return ["- None"]
    return [f"- `{item['capability']}`: {item['reason']}" for item in failures]


def summary(output_dir: Path, stem: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "json": str(output_dir / f"{stem}.json"),
        "markdown": str(output_dir / f"{stem}.md"),
        "status": result["status"],
    }


def first_value(rows: list[dict[str, Any]], field: str) -> str:
    if not rows:
        return ""
    return str(rows[0].get(field) or "")
