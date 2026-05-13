from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.config import DEFAULT_OUTPUT_DIR
from src.orchestrator import run_pipeline

REAL_FUND_SMOKE_SET = [
    {"fund_code": "161725", "scenario": "baijiu_consumption"},
    {"fund_code": "320007", "scenario": "semiconductor"},
    {"fund_code": "003096", "scenario": "healthcare"},
    {"fund_code": "003834", "scenario": "new_energy"},
    {"fund_code": "001475", "scenario": "defense"},
    {"fund_code": "000991", "scenario": "real_estate"},
]


Runner = Callable[[str, str, Path], dict[str, Path]]


def run_real_fund_smoke(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    fund_specs: list[dict[str, str]] | None = None,
    runner: Runner = run_pipeline,
    min_coverage_ratio: float = 0.75,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    fund_specs = fund_specs or REAL_FUND_SMOKE_SET

    fund_results = []
    for spec in fund_specs:
        fund_code = spec["fund_code"]
        try:
            artifacts = runner(
                fund_code=fund_code,
                provider_mode="eastmoney",
                output_dir=output_path,
            )
            fund_results.append(
                _build_fund_result(
                    fund_code=fund_code,
                    scenario=spec["scenario"],
                    scoring_path=Path(artifacts["scoring"]),
                    min_coverage_ratio=min_coverage_ratio,
                )
            )
        except Exception as exc:
            fund_results.append(
                _build_failed_fund_result(
                    fund_code=fund_code,
                    scenario=spec["scenario"],
                    error=exc,
                )
            )

    summary = {
        "status": "passed"
        if all(result["coverage_passed"] for result in fund_results)
        else "failed",
        "provider_mode": "eastmoney",
        "min_coverage_ratio": min_coverage_ratio,
        "fund_count": len(fund_results),
        "funds": fund_results,
    }
    _write_summary(summary, output_path)
    return summary


def _build_fund_result(
    fund_code: str,
    scenario: str,
    scoring_path: Path,
    min_coverage_ratio: float,
) -> dict[str, Any]:
    scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
    coverage = scoring["mapping_coverage"]
    primary = scoring["primary_narrative"] or {
        "name": None,
        "state": {
            "stage": None,
            "sustainability_score": None,
            "confidence": None,
        },
    }
    coverage_ratio = coverage["coverage_ratio"]
    provider_foundation = scoring.get("provider_foundation", {})
    unmapped_holdings = _summarize_unmapped_holdings(scoring["unmapped_holdings"])
    return {
        "fund_code": fund_code,
        "scenario": scenario,
        "status": "passed",
        "data_quality": scoring["metadata"]["data_quality"],
        "effective_data_quality": provider_foundation.get(
            "effective_data_quality", scoring["metadata"]["data_quality"]
        ),
        "data_source_notice_required": bool(
            provider_foundation.get("disclosure_required")
        ),
        "data_source_notice": provider_foundation.get("disclosure_message", ""),
        "as_of_date": scoring["metadata"]["as_of_date"],
        "primary_narrative": primary["name"],
        "stage": primary["state"]["stage"],
        "sustainability_score": primary["state"]["sustainability_score"],
        "confidence": primary["state"]["confidence"],
        "coverage_ratio": coverage_ratio,
        "coverage_passed": coverage_ratio >= min_coverage_ratio,
        "covered_holding_count": coverage["covered_holding_count"],
        "total_holding_count": coverage["total_holding_count"],
        "mapping_methods": coverage["mapping_methods"],
        "unmapped_holding_count": len(unmapped_holdings),
        "unmapped_holdings": unmapped_holdings,
        "degradation_event_count": len(scoring["degradation_events"]),
        "error": None,
    }


def _build_failed_fund_result(
    fund_code: str,
    scenario: str,
    error: Exception,
) -> dict[str, Any]:
    message = " ".join(str(error).split()) or error.__class__.__name__
    return {
        "fund_code": fund_code,
        "scenario": scenario,
        "status": "failed",
        "data_quality": "unavailable",
        "effective_data_quality": "unavailable",
        "data_source_notice_required": True,
        "data_source_notice": "Provider run failed; no reliable data source foundation is available.",
        "as_of_date": None,
        "primary_narrative": None,
        "stage": None,
        "sustainability_score": None,
        "confidence": None,
        "coverage_ratio": 0,
        "coverage_passed": False,
        "covered_holding_count": 0,
        "total_holding_count": 0,
        "mapping_methods": {},
        "unmapped_holding_count": 0,
        "unmapped_holdings": [],
        "degradation_event_count": 1,
        "error": message,
    }


def _summarize_unmapped_holdings(
    unmapped_holdings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "stock_code": holding.get("stock_code"),
            "stock_name": holding.get("stock_name"),
            "industry": holding.get("industry"),
            "weight": holding.get("weight"),
        }
        for holding in unmapped_holdings
    ]


def _write_summary(summary: dict[str, Any], output_path: Path) -> None:
    (output_path / "real_fund_smoke_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Real Fund Smoke Summary",
        "",
        f"- Status: {summary['status']}",
        f"- Provider mode: {summary['provider_mode']}",
        f"- Minimum coverage ratio: {summary['min_coverage_ratio']:.0%}",
        "",
        "| Fund | Scenario | Status | Data Quality | Notice | Primary Narrative | Stage | Coverage | Methods | Error |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for result in summary["funds"]:
        methods = ", ".join(
            f"{method}: {count}"
            for method, count in sorted(result["mapping_methods"].items())
        ) or "-"
        lines.append(
            "| "
            f"{result['fund_code']} | "
            f"{result['scenario']} | "
            f"{result['status']} | "
            f"{result['effective_data_quality']} | "
            f"{'yes' if result['data_source_notice_required'] else 'no'} | "
            f"{result['primary_narrative'] or '-'} | "
            f"{result['stage'] or '-'} | "
            f"{result['coverage_ratio']:.0%} | "
            f"{methods} | "
            f"{result['error'] or '-'} |"
        )
    lines.append("")
    mapping_gap_results = [
        result for result in summary["funds"] if result["unmapped_holdings"]
    ]
    if mapping_gap_results:
        lines.extend(
            [
                "## Mapping Gaps",
                "",
                "| Fund | Stock | Name | Industry | Weight |",
                "| --- | --- | --- | --- | ---: |",
            ]
        )
        for result in mapping_gap_results:
            for holding in result["unmapped_holdings"]:
                lines.append(
                    "| "
                    f"{result['fund_code']} | "
                    f"{holding['stock_code'] or '-'} | "
                    f"{holding['stock_name'] or '-'} | "
                    f"{holding['industry'] or '-'} | "
                    f"{_format_weight(holding['weight'])} |"
                )
        lines.append("")
    (output_path / "real_fund_smoke_summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def _format_weight(weight: Any) -> str:
    if isinstance(weight, int | float):
        return f"{weight:.2%}"
    return "-"
