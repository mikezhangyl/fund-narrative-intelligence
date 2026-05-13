from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import DEFAULT_OUTPUT_DIR, VERSION_DEFAULTS
from src.modules.fund_analysis.aggregation import aggregate_fund_narratives
from src.modules.fund_analysis.mapping import build_mapping_result
from src.modules.report_writer.interpretation import interpret_narrative
from src.modules.report_writer.writer import write_reports
from src.modules.signal_service.scoring import score_narrative_state
from src.modules.snapshot_writer.writer import write_json_artifact
from src.providers.factory import select_data_provider
from src.providers.mock import MockDataProvider


def run_pipeline(
    fund_code: str,
    provider_mode: str = "mock",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    if not fund_code.isdigit():
        raise ValueError("fund_code must contain digits only")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    provider_selection = select_data_provider(provider_mode)
    provider = provider_selection.provider
    fund_payload = provider.get_fund_holdings(fund_code)
    registry_payload = provider.get_narrative_registry()
    all_mappings = provider.get_stock_narrative_mappings()
    evidence = provider.get_evidence()
    signal_events = provider.get_signal_events()

    fund = fund_payload["fund"]
    holdings = fund_payload["holdings"]
    as_of_date = fund_payload["as_of_date"]
    registry_items = registry_payload["narratives"]
    registry_by_id = {item["narrative_id"]: item for item in registry_items}
    mapping_result = build_mapping_result(
        holdings=holdings,
        mappings=all_mappings,
        registry=registry_by_id,
    )
    selected_mappings = mapping_result["mappings"]
    exposures = aggregate_fund_narratives(
        holdings=holdings,
        mappings=selected_mappings,
        registry=registry_by_id,
    )
    narrative_results = [
        _with_state(
            exposure=exposure,
            signal_events=signal_events,
            evidence=evidence,
            as_of_date=as_of_date,
            data_quality=fund["provider_metadata"]["data_quality"],
        )
        for exposure in exposures
    ]

    primary_narrative = narrative_results[0] if narrative_results else None
    secondary_narratives = narrative_results[1:4]
    metadata = _metadata(
        fund_code=fund_code,
        as_of_date=as_of_date,
        data_quality=fund["provider_metadata"]["data_quality"],
    )
    degradation_events = [
        *provider_selection.degradation_events,
        *getattr(provider, "degradation_events", []),
    ]
    raw_payload = {
        "metadata": metadata,
        "fund": fund,
        "holdings": holdings,
        "narrative_registry_version": registry_payload["version"],
        "narrative_registry": registry_items,
        "stock_narrative_mappings": selected_mappings,
        "mapping_coverage": mapping_result["coverage"],
        "unmapped_holdings": mapping_result["unmapped_holdings"],
        "evidence": evidence,
        "signal_events": signal_events,
        "degradation_events": degradation_events,
    }
    scoring_payload = {
        "metadata": metadata,
        "fund": fund,
        "holdings": holdings,
        "primary_narrative": primary_narrative,
        "secondary_narratives": secondary_narratives,
        "all_narratives": narrative_results,
        "mapping_coverage": mapping_result["coverage"],
        "unmapped_holdings": mapping_result["unmapped_holdings"],
        "supporting_evidence": _top_evidence(
            evidence, narrative_results, sentiments={"positive", "mixed"}
        ),
        "risk_evidence": _top_evidence(evidence, narrative_results, sentiments={"negative"}),
        "degradation_events": degradation_events,
    }

    raw_path = output_path / f"fund_{fund_code}_raw.json"
    scoring_path = output_path / f"fund_{fund_code}_scoring.json"
    write_json_artifact(raw_payload, raw_path)
    write_json_artifact(scoring_payload, scoring_path)
    report_paths = write_reports(scoring_payload, output_path)

    return {
        "raw": raw_path,
        "scoring": scoring_path,
        "markdown": report_paths["markdown"],
        "html": report_paths["html"],
    }


def run_all_fixture_pipelines(
    provider_mode: str = "mock",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, Any]]:
    provider = MockDataProvider()
    return {
        fund_code: run_pipeline(
            fund_code=fund_code,
            provider_mode=provider_mode,
            output_dir=output_dir,
        )
        for fund_code in provider.list_fund_codes()
    }


def _with_state(
    exposure: dict[str, Any],
    signal_events: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    as_of_date: str,
    data_quality: str,
) -> dict[str, Any]:
    narrative_id = exposure["narrative_id"]
    evidence_count = sum(1 for item in evidence if item["narrative_id"] == narrative_id)
    result = {
        **exposure,
        "state": score_narrative_state(
            narrative_id=narrative_id,
            signal_events=signal_events,
            mapping_confidence=exposure["confidence"],
            evidence_count=evidence_count,
            as_of_date=as_of_date,
            data_quality=data_quality,
        ),
    }
    result["interpretation"] = interpret_narrative(result)
    return result


def _metadata(fund_code: str, as_of_date: str, data_quality: str) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    input_hash = hashlib.sha256(
        f"{fund_code}|{as_of_date}|{VERSION_DEFAULTS}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "run_id": f"run_{fund_code}_{created_at}",
        "fund_code": fund_code,
        "created_at": created_at,
        "as_of_date": as_of_date,
        "input_hash": input_hash,
        "data_snapshot_id": f"snapshot_{fund_code}_{input_hash}",
        "data_quality": data_quality,
        **VERSION_DEFAULTS,
    }


def _top_evidence(
    evidence: list[dict[str, Any]],
    narrative_results: list[dict[str, Any]],
    sentiments: set[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    narrative_ids = {item["narrative_id"] for item in narrative_results[:4]}
    filtered = [
        item
        for item in evidence
        if item["narrative_id"] in narrative_ids and item["sentiment"] in sentiments
    ]
    return sorted(
        filtered,
        key=lambda item: (item.get("confidence", 0), item.get("event_date", "")),
        reverse=True,
    )[:limit]
