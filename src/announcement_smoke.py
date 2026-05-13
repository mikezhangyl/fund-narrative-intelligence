from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.config import DEFAULT_OUTPUT_DIR
from src.orchestrator import run_pipeline

ANNOUNCEMENT_EVIDENCE_SMOKE_SET = [
    {
        "fund_code": "161725",
        "scenario": "baijiu_cninfo_metadata",
        "provider_mode": "eastmoney",
        "announcement_start_date": "2026-01-01",
        "min_announcement_count": 1,
    }
]


Runner = Callable[..., dict[str, Path]]


def run_announcement_evidence_smoke(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    fund_specs: list[dict[str, Any]] | None = None,
    runner: Runner = run_pipeline,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    fund_specs = fund_specs or ANNOUNCEMENT_EVIDENCE_SMOKE_SET

    case_results = [
        _run_smoke_case(spec=spec, output_path=output_path, runner=runner)
        for spec in fund_specs
    ]
    summary = {
        "status": "passed"
        if all(result["status"] == "passed" for result in case_results)
        else "failed",
        "provider_mode": "eastmoney",
        "cases": case_results,
    }
    _write_summary(summary, output_path)
    return summary


def _run_smoke_case(
    spec: dict[str, Any],
    output_path: Path,
    runner: Runner,
) -> dict[str, Any]:
    fund_code = str(spec["fund_code"])
    scenario = str(spec["scenario"])
    provider_mode = str(spec.get("provider_mode", "eastmoney"))
    announcement_start_date = str(spec["announcement_start_date"])
    min_announcement_count = int(spec.get("min_announcement_count", 1))

    try:
        artifacts = runner(
            fund_code=fund_code,
            provider_mode=provider_mode,
            output_dir=output_path,
            include_announcement_evidence=True,
            announcement_start_date=announcement_start_date,
        )
        return _build_case_result(
            fund_code=fund_code,
            scenario=scenario,
            provider_mode=provider_mode,
            announcement_start_date=announcement_start_date,
            min_announcement_count=min_announcement_count,
            raw_path=Path(artifacts["raw"]),
            scoring_path=Path(artifacts["scoring"]),
        )
    except Exception as exc:
        return _build_failed_case_result(
            fund_code=fund_code,
            scenario=scenario,
            provider_mode=provider_mode,
            announcement_start_date=announcement_start_date,
            min_announcement_count=min_announcement_count,
            error=exc,
        )


def _build_case_result(
    fund_code: str,
    scenario: str,
    provider_mode: str,
    announcement_start_date: str,
    min_announcement_count: int,
    raw_path: Path,
    scoring_path: Path,
) -> dict[str, Any]:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
    announcements = raw.get("announcements", {})
    announcement_evidence = raw.get("announcement_evidence", {})
    provider_foundation = scoring.get("provider_foundation", {})
    announcement_layer = provider_foundation.get("layers", {}).get("announcements", {})
    announcement_count = len(announcements.get("announcements") or [])
    announcement_evidence_count = len(announcement_evidence.get("evidence") or [])
    announcement_data_quality = str(announcements.get("data_quality", "unavailable"))
    announcement_provider = str(announcement_layer.get("provider_name", ""))
    announcement_layer_quality = str(
        announcement_layer.get("data_quality", "unavailable")
    )
    data_source_notice = str(provider_foundation.get("disclosure_message", ""))
    announcement_check_passed = (
        announcement_count >= min_announcement_count
        and announcement_evidence_count >= min_announcement_count
        and announcement_data_quality in {"fresh", "partial"}
    )
    announcement_layer_check_passed = (
        announcement_provider.startswith("cninfo")
        and not bool(announcement_layer.get("is_mock"))
        and announcement_layer_quality in {"fresh", "partial"}
    )
    notice_check_passed = bool(provider_foundation.get("disclosure_required")) and (
        "Mock" in data_source_notice
        or "mock" in data_source_notice
        or "混合数据源" in data_source_notice
        or "完整真实环境输出" in data_source_notice
    )
    status = (
        "passed"
        if (
            announcement_check_passed
            and announcement_layer_check_passed
            and notice_check_passed
        )
        else "failed"
    )

    return {
        "fund_code": fund_code,
        "scenario": scenario,
        "provider_mode": provider_mode,
        "status": status,
        "as_of_date": raw.get("metadata", {}).get("as_of_date"),
        "announcement_start_date": announcement_start_date,
        "min_announcement_count": min_announcement_count,
        "announcement_count": announcement_count,
        "announcement_evidence_count": announcement_evidence_count,
        "announcement_data_quality": announcement_data_quality,
        "announcement_provider": announcement_provider,
        "announcement_layer_data_quality": announcement_layer_quality,
        "announcement_check_passed": announcement_check_passed,
        "announcement_layer_check_passed": announcement_layer_check_passed,
        "missing_stock_count": len(announcements.get("missing_stock_codes") or []),
        "effective_data_quality": provider_foundation.get("effective_data_quality"),
        "data_source_notice_required": bool(
            provider_foundation.get("disclosure_required")
        ),
        "data_source_notice": data_source_notice,
        "notice_check_passed": notice_check_passed,
        "degradation_event_count": len(scoring.get("degradation_events") or []),
        "error": None,
    }


def _build_failed_case_result(
    fund_code: str,
    scenario: str,
    provider_mode: str,
    announcement_start_date: str,
    min_announcement_count: int,
    error: Exception,
) -> dict[str, Any]:
    message = " ".join(str(error).split()) or error.__class__.__name__
    return {
        "fund_code": fund_code,
        "scenario": scenario,
        "provider_mode": provider_mode,
        "status": "failed",
        "as_of_date": None,
        "announcement_start_date": announcement_start_date,
        "min_announcement_count": min_announcement_count,
        "announcement_count": 0,
        "announcement_evidence_count": 0,
        "announcement_data_quality": "unavailable",
        "announcement_provider": None,
        "announcement_layer_data_quality": "unavailable",
        "announcement_check_passed": False,
        "announcement_layer_check_passed": False,
        "missing_stock_count": 0,
        "effective_data_quality": "unavailable",
        "data_source_notice_required": True,
        "data_source_notice": (
            "Announcement evidence smoke failed; no reliable CNINFO disclosure "
            "state is available."
        ),
        "notice_check_passed": False,
        "degradation_event_count": 1,
        "error": message,
    }


def _write_summary(summary: dict[str, Any], output_path: Path) -> None:
    (output_path / "announcement_evidence_smoke_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Announcement Evidence Smoke Summary",
        "",
        f"- Status: {summary['status']}",
        f"- Provider mode: {summary['provider_mode']}",
        "",
        "| Fund | Scenario | Status | Announcements | Evidence | Quality | Notice | Error |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for result in summary["cases"]:
        lines.append(
            "| "
            f"{result['fund_code']} | "
            f"{result['scenario']} | "
            f"{result['status']} | "
            f"{result['announcement_count']} | "
            f"{result['announcement_evidence_count']} | "
            f"{result['effective_data_quality']} | "
            f"{'yes' if result['notice_check_passed'] else 'no'} | "
            f"{result['error'] or '-'} |"
        )
    lines.append("")
    (output_path / "announcement_evidence_smoke_summary.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
