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
                    raw_path=Path(artifacts["raw"]) if "raw" in artifacts else None,
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
    raw_path: Path | None,
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
    multi_mapped_holdings = _summarize_multi_mapped_holdings(raw_path)
    mapping_precision_flags = _summarize_mapping_precision_flags(scoring)
    excluded_mapping_candidates = _summarize_excluded_mapping_candidates(scoring)
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
        "multi_mapped_holding_count": len(multi_mapped_holdings),
        "multi_mapped_holdings": multi_mapped_holdings,
        "mapping_precision_flag_count": len(mapping_precision_flags),
        "mapping_precision_flags": mapping_precision_flags,
        "excluded_mapping_candidate_count": len(excluded_mapping_candidates),
        "excluded_mapping_candidates": excluded_mapping_candidates,
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
        "multi_mapped_holding_count": 0,
        "multi_mapped_holdings": [],
        "mapping_precision_flag_count": 0,
        "mapping_precision_flags": [],
        "excluded_mapping_candidate_count": 0,
        "excluded_mapping_candidates": [],
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


def _summarize_multi_mapped_holdings(raw_path: Path | None) -> list[dict[str, Any]]:
    if raw_path is None or not raw_path.exists():
        return []
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    holdings_by_code = {
        holding["stock_code"]: holding for holding in raw.get("holdings", [])
    }
    registry_by_id = {
        item["narrative_id"]: item for item in raw.get("narrative_registry", [])
    }
    mappings_by_stock: dict[str, list[dict[str, Any]]] = {}
    for mapping in raw.get("stock_narrative_mappings", []):
        stock_code = mapping.get("stock_code")
        if not stock_code:
            continue
        mappings_by_stock.setdefault(str(stock_code), []).append(mapping)

    results = []
    for stock_code, mappings in sorted(mappings_by_stock.items()):
        narrative_ids = _unique_in_order(
            str(mapping["narrative_id"])
            for mapping in mappings
            if mapping.get("narrative_id")
        )
        if len(narrative_ids) < 2:
            continue
        holding = holdings_by_code.get(stock_code, {})
        results.append(
            {
                "stock_code": stock_code,
                "stock_name": holding.get("stock_name"),
                "industry": holding.get("industry"),
                "weight": holding.get("weight"),
                "narratives": [
                    registry_by_id.get(narrative_id, {}).get("name", narrative_id)
                    for narrative_id in narrative_ids
                ],
                "narrative_ids": narrative_ids,
                "methods": _unique_in_order(
                    str(mapping.get("method", "unknown")) for mapping in mappings
                ),
            }
        )
    return results


def _summarize_mapping_precision_flags(
    scoring: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "type": flag.get("type"),
            "severity": flag.get("severity"),
            "stock_code": flag.get("stock_code"),
            "stock_name": flag.get("stock_name"),
            "industry": flag.get("industry"),
            "weight": flag.get("weight"),
            "mapping_method": flag.get("mapping_method"),
            "narrative_ids": flag.get("narrative_ids", []),
            "narratives": flag.get("narratives", []),
            "confidence_before": flag.get("confidence_before"),
            "confidence_after": flag.get("confidence_after"),
            "recommended_action": flag.get("recommended_action"),
        }
        for flag in scoring.get("mapping_precision_flags", [])
    ]


def _summarize_excluded_mapping_candidates(
    scoring: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "type": candidate.get("type"),
            "exclusion_id": candidate.get("exclusion_id"),
            "stock_code": candidate.get("stock_code"),
            "stock_name": candidate.get("stock_name"),
            "industry": candidate.get("industry"),
            "weight": candidate.get("weight"),
            "narrative_id": candidate.get("narrative_id"),
            "narrative_name": candidate.get("narrative_name"),
            "method": candidate.get("method"),
            "matched_terms": candidate.get("matched_terms", []),
            "reason": candidate.get("reason"),
            "recommended_action": candidate.get("recommended_action"),
        }
        for candidate in scoring.get("excluded_mapping_candidates", [])
    ]


def _unique_in_order(values: Any) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


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
    multi_match_results = [
        result for result in summary["funds"] if result["multi_mapped_holdings"]
    ]
    if multi_match_results:
        lines.extend(
            [
                "## Multi-Mapped Holdings",
                "",
                "| Fund | Stock | Name | Industry | Weight | Narratives | Methods |",
                "| --- | --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for result in multi_match_results:
            for holding in result["multi_mapped_holdings"]:
                lines.append(
                    "| "
                    f"{result['fund_code']} | "
                    f"{holding['stock_code'] or '-'} | "
                    f"{holding['stock_name'] or '-'} | "
                    f"{holding['industry'] or '-'} | "
                    f"{_format_weight(holding['weight'])} | "
                    f"{', '.join(holding['narratives']) or '-'} | "
                    f"{', '.join(holding['methods']) or '-'} |"
                )
        lines.append("")
    precision_flag_results = [
        result for result in summary["funds"] if result["mapping_precision_flags"]
    ]
    if precision_flag_results:
        lines.extend(
            [
                "## Mapping Precision Flags",
                "",
                "| Fund | Stock | Name | Type | Severity | Industry | Narratives | Confidence | Action |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for result in precision_flag_results:
            for flag in result["mapping_precision_flags"]:
                lines.append(
                    "| "
                    f"{result['fund_code']} | "
                    f"{flag['stock_code'] or '-'} | "
                    f"{flag['stock_name'] or '-'} | "
                    f"{flag['type'] or '-'} | "
                    f"{flag['severity'] or '-'} | "
                    f"{flag['industry'] or '-'} | "
                    f"{', '.join(flag['narratives']) or '-'} | "
                    f"{_format_confidence_change(flag)} | "
                    f"{flag['recommended_action'] or '-'} |"
                )
        lines.append("")
    excluded_candidate_results = [
        result for result in summary["funds"] if result["excluded_mapping_candidates"]
    ]
    if excluded_candidate_results:
        lines.extend(
            [
                "## Excluded Mapping Candidates",
                "",
                "| Fund | Stock | Name | Industry | Candidate Narrative | Terms | Action | Reason |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for result in excluded_candidate_results:
            for candidate in result["excluded_mapping_candidates"]:
                lines.append(
                    "| "
                    f"{result['fund_code']} | "
                    f"{candidate['stock_code'] or '-'} | "
                    f"{candidate['stock_name'] or '-'} | "
                    f"{candidate['industry'] or '-'} | "
                    f"{candidate['narrative_name'] or candidate['narrative_id'] or '-'} | "
                    f"{', '.join(candidate['matched_terms']) or '-'} | "
                    f"{candidate['recommended_action'] or '-'} | "
                    f"{candidate['reason'] or '-'} |"
                )
        lines.append("")
    (output_path / "real_fund_smoke_summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def _format_confidence_change(flag: dict[str, Any]) -> str:
    before = flag.get("confidence_before")
    after = flag.get("confidence_after")
    if isinstance(before, int | float) and isinstance(after, int | float):
        return f"{before:.2f} -> {after:.2f}"
    return "-"


def _format_weight(weight: Any) -> str:
    if isinstance(weight, int | float):
        return f"{weight:.2%}"
    return "-"
