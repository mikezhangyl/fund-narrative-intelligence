from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.config import DEFAULT_OUTPUT_DIR, VERSION_DEFAULTS
from src.modules.evidence.announcements import convert_announcements_to_evidence
from src.modules.fund_analysis.aggregation import aggregate_fund_narratives
from src.modules.fund_analysis.mapping import build_mapping_result
from src.modules.narrative_review.queue import build_candidate_review_queue
from src.modules.report_writer.interpretation import interpret_narrative
from src.modules.report_writer.writer import write_reports
from src.modules.signal_service.scoring import score_narrative_state
from src.modules.snapshot_writer.writer import write_json_artifact
from src.providers.cninfo import (
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNInfoAnnouncementProvider,
)
from src.providers.eastmoney_market import EastmoneyMarketDataProvider
from src.providers.factory import select_data_provider
from src.providers.mock import MockDataProvider
from src.providers.provenance import build_provider_foundation


def run_pipeline(
    fund_code: str,
    provider_mode: str = "mock",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    include_announcement_evidence: bool = False,
    announcement_start_date: str | None = None,
    announcement_provider: Any | None = None,
    include_market_quotes: bool = False,
    market_data_provider: Any | None = None,
) -> dict[str, Any]:
    if not fund_code.isdigit():
        raise ValueError("fund_code must contain digits only")
    if announcement_start_date is not None:
        _require_iso_date(announcement_start_date, "announcement_start_date")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    provider_selection = select_data_provider(provider_mode)
    provider = provider_selection.provider
    fund_payload = provider.get_fund_holdings(fund_code)
    registry_payload = provider.get_narrative_registry()
    all_mappings = provider.get_stock_narrative_mappings()
    mapping_exclusions_payload = provider.get_mapping_exclusions()
    evidence = provider.get_evidence()
    signal_events = provider.get_signal_events()

    fund = fund_payload["fund"]
    holdings = fund_payload["holdings"]
    as_of_date = fund_payload["as_of_date"]
    registry_items = registry_payload["narratives"]
    candidate_narratives = registry_payload.get("candidate_narratives", [])
    registry_by_id = {item["narrative_id"]: item for item in registry_items}
    mapping_result = build_mapping_result(
        holdings=holdings,
        mappings=all_mappings,
        registry=registry_by_id,
        exclusions=mapping_exclusions_payload["exclusions"],
    )
    selected_mappings = mapping_result["mappings"]
    in_scope_candidate_narratives = _candidate_narratives_for_excluded_candidates(
        candidate_narratives=candidate_narratives,
        excluded_mapping_candidates=mapping_result["excluded_mapping_candidates"],
    )
    candidate_review_queue = build_candidate_review_queue(
        candidate_narratives=in_scope_candidate_narratives,
        excluded_mapping_candidates=mapping_result["excluded_mapping_candidates"],
    )
    degradation_events = [
        *provider_selection.degradation_events,
        *getattr(provider, "degradation_events", []),
    ]
    announcements_payload: dict[str, Any] | None = None
    announcement_evidence_payload: dict[str, Any] | None = None
    announcement_layer: dict[str, Any] | None = None
    market_quotes_payload: dict[str, Any] | None = None
    market_quotes_layer: dict[str, Any] | None = None
    if include_market_quotes:
        market_result = _run_market_quotes(
            stock_codes=[holding["stock_code"] for holding in holdings],
            market_data_provider=market_data_provider,
        )
        market_quotes_payload = market_result["market_quotes"]
        market_quotes_layer = market_result["provider_layer"]
        degradation_events = [
            *degradation_events,
            *market_result["degradation_events"],
        ]
    if include_announcement_evidence:
        announcement_result = _run_announcement_evidence(
            stock_codes=[holding["stock_code"] for holding in holdings],
            stock_mappings=selected_mappings,
            as_of_date=as_of_date,
            start_date=announcement_start_date,
            announcement_provider=announcement_provider,
        )
        announcements_payload = announcement_result["announcements"]
        announcement_evidence_payload = announcement_result["announcement_evidence"]
        announcement_layer = announcement_result["provider_layer"]
        degradation_events = [
            *degradation_events,
            *announcement_result["degradation_events"],
        ]
        evidence = [
            *evidence,
            *announcement_evidence_payload["evidence"],
        ]

    provider_foundation = _provider_foundation_with_optional_announcement_layer(
        provider=provider,
        fund_provider_metadata=fund["provider_metadata"],
        degradation_events=degradation_events,
        announcement_layer=announcement_layer,
        market_quotes_layer=market_quotes_layer,
    )
    effective_data_quality = provider_foundation["effective_data_quality"]
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
            data_quality=effective_data_quality,
        )
        for exposure in exposures
    ]

    primary_narrative = narrative_results[0] if narrative_results else None
    secondary_narratives = narrative_results[1:4]
    metadata = _metadata(
        fund_code=fund_code,
        as_of_date=as_of_date,
        data_quality=effective_data_quality,
    )
    raw_payload = {
        "metadata": metadata,
        "fund": fund,
        "holdings": holdings,
        "provider_foundation": provider_foundation,
        "narrative_registry_version": registry_payload["version"],
        "narrative_registry": registry_items,
        "candidate_narrative_registry_version": registry_payload["version"],
        "candidate_narratives": in_scope_candidate_narratives,
        "candidate_review_queue": candidate_review_queue,
        "stock_narrative_mappings": selected_mappings,
        "mapping_exclusions_version": mapping_exclusions_payload["version"],
        "mapping_exclusions": mapping_exclusions_payload["exclusions"],
        "mapping_coverage": mapping_result["coverage"],
        "mapping_rationales": mapping_result["mapping_rationales"],
        "mapping_precision_flags": mapping_result["mapping_precision_flags"],
        "excluded_mapping_candidates": mapping_result[
            "excluded_mapping_candidates"
        ],
        "unmapped_holdings": mapping_result["unmapped_holdings"],
        "evidence": evidence,
        "signal_events": signal_events,
        "degradation_events": degradation_events,
    }
    if announcements_payload is not None and announcement_evidence_payload is not None:
        raw_payload["announcements"] = announcements_payload
        raw_payload["announcement_evidence"] = announcement_evidence_payload
    if market_quotes_payload is not None:
        raw_payload["market_quotes"] = market_quotes_payload

    scoring_payload = {
        "metadata": metadata,
        "fund": fund,
        "holdings": holdings,
        "primary_narrative": primary_narrative,
        "secondary_narratives": secondary_narratives,
        "all_narratives": narrative_results,
        "provider_foundation": provider_foundation,
        "mapping_coverage": mapping_result["coverage"],
        "mapping_rationales": mapping_result["mapping_rationales"],
        "mapping_precision_flags": mapping_result["mapping_precision_flags"],
        "excluded_mapping_candidates": mapping_result[
            "excluded_mapping_candidates"
        ],
        "candidate_narratives": in_scope_candidate_narratives,
        "candidate_review_queue": candidate_review_queue,
        "unmapped_holdings": mapping_result["unmapped_holdings"],
        "supporting_evidence": _top_evidence(
            evidence, narrative_results, sentiments={"positive", "mixed"}
        ),
        "risk_evidence": _top_evidence(evidence, narrative_results, sentiments={"negative"}),
        "degradation_events": degradation_events,
    }
    if announcement_evidence_payload is not None:
        scoring_payload["announcement_evidence"] = announcement_evidence_payload
    if market_quotes_payload is not None:
        scoring_payload["market_quotes"] = market_quotes_payload

    review_queue_payload = {
        "metadata": metadata,
        "fund": fund,
        "provider_foundation": provider_foundation,
        "candidate_review_queue": candidate_review_queue,
        "candidate_narratives": in_scope_candidate_narratives,
        "excluded_mapping_candidates": mapping_result[
            "excluded_mapping_candidates"
        ],
    }

    raw_path = output_path / f"fund_{fund_code}_raw.json"
    scoring_path = output_path / f"fund_{fund_code}_scoring.json"
    review_queue_path = output_path / f"fund_{fund_code}_review_queue.json"
    manifest_path = output_path / f"fund_{fund_code}_manifest.json"
    write_json_artifact(raw_payload, raw_path)
    write_json_artifact(scoring_payload, scoring_path)
    write_json_artifact(review_queue_payload, review_queue_path)
    report_paths = write_reports(scoring_payload, output_path)
    manifest_payload = _artifact_manifest(
        fund_code=fund_code,
        as_of_date=as_of_date,
        provider_mode=provider_mode,
        data_quality=effective_data_quality,
        provider_foundation=provider_foundation,
        degradation_events=degradation_events,
        artifact_paths={
            "raw": raw_path,
            "scoring": scoring_path,
            "review_queue": review_queue_path,
            "markdown": report_paths["markdown"],
            "html": report_paths["html"],
        },
    )
    write_json_artifact(manifest_payload, manifest_path)

    return {
        "raw": raw_path,
        "scoring": scoring_path,
        "review_queue": review_queue_path,
        "manifest": manifest_path,
        "markdown": report_paths["markdown"],
        "html": report_paths["html"],
    }


def _candidate_narratives_for_excluded_candidates(
    candidate_narratives: list[dict[str, Any]],
    excluded_mapping_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exclusion_ids = {
        str(candidate["exclusion_id"])
        for candidate in excluded_mapping_candidates
        if candidate.get("exclusion_id")
    }
    stock_codes = {
        str(candidate["stock_code"])
        for candidate in excluded_mapping_candidates
        if candidate.get("stock_code")
    }
    in_scope = []
    for candidate_narrative in candidate_narratives:
        related_exclusion_ids = set(candidate_narrative.get("related_exclusion_ids", []))
        triggering_stock_codes = set(candidate_narrative.get("triggering_stock_codes", []))
        if related_exclusion_ids & exclusion_ids or triggering_stock_codes & stock_codes:
            in_scope.append(candidate_narrative)
    return in_scope


def _artifact_manifest(
    fund_code: str,
    as_of_date: str,
    provider_mode: str,
    data_quality: str,
    provider_foundation: dict[str, Any],
    degradation_events: list[dict[str, str]],
    artifact_paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "version": "pipeline-artifact-manifest-v1",
        "fund_code": fund_code,
        "as_of_date": as_of_date,
        "provider_mode": provider_mode,
        "data_quality": data_quality,
        "web_ready": True,
        "provider_foundation": provider_foundation,
        "degradation_events": degradation_events,
        "artifacts": {
            key: {
                "path": path.name,
                "format": _artifact_format(path),
            }
            for key, path in artifact_paths.items()
        },
    }


def _artifact_format(path: Path) -> str:
    if path.suffix == ".json":
        return "json"
    if path.suffix == ".md":
        return "markdown"
    if path.suffix == ".html":
        return "html"
    return path.suffix.removeprefix(".") or "unknown"


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


def inspect_provider_foundation(
    fund_code: str,
    provider_mode: str = "mock",
) -> dict[str, Any]:
    if not fund_code.isdigit():
        raise ValueError("fund_code must contain digits only")

    provider_selection = select_data_provider(provider_mode)
    provider = provider_selection.provider
    fund_payload = provider.get_fund_holdings(fund_code)
    fund = fund_payload["fund"]
    degradation_events = [
        *provider_selection.degradation_events,
        *getattr(provider, "degradation_events", []),
    ]
    provider_foundation = provider.get_provider_foundation(
        fund_provider_metadata=fund["provider_metadata"],
        degradation_events=degradation_events,
    )
    return {
        "fund_code": fund_code,
        "provider_mode": provider_mode,
        "as_of_date": fund_payload["as_of_date"],
        "fund": fund,
        "provider_foundation": provider_foundation,
    }


def _run_announcement_evidence(
    stock_codes: list[str],
    stock_mappings: list[dict[str, Any]],
    as_of_date: str,
    start_date: str | None,
    announcement_provider: Any | None,
) -> dict[str, Any]:
    provider = announcement_provider or CNInfoAnnouncementProvider()
    degradation_events: list[dict[str, str]] = []
    try:
        announcements_payload = provider.get_announcements(
            stock_codes=stock_codes,
            as_of_date=as_of_date,
            start_date=start_date,
        )
    except Exception as exc:
        provider_name = str(getattr(provider, "provider_name", "announcement-provider"))
        degradation_events.append(
            {
                "type": "provider_unavailable",
                "provider_name": provider_name,
                "reason": f"Announcement provider failed: {exc}",
            }
        )
        announcements_payload = {
            "version": str(getattr(provider, "provider_version", "announcement-v1")),
            "data_quality": "unavailable",
            "announcements": [],
            "missing_stock_codes": sorted(set(stock_codes)),
        }

    degradation_events = [
        *degradation_events,
        *getattr(provider, "degradation_events", []),
    ]
    announcement_evidence_payload = convert_announcements_to_evidence(
        announcements_payload=announcements_payload,
        stock_mappings=stock_mappings,
        as_of_date=as_of_date,
    )
    return {
        "announcements": announcements_payload,
        "announcement_evidence": announcement_evidence_payload,
        "provider_layer": _announcement_provider_layer(
            provider=provider,
            announcements_payload=announcements_payload,
        ),
        "degradation_events": degradation_events,
    }


def _run_market_quotes(
    stock_codes: list[str],
    market_data_provider: Any | None,
) -> dict[str, Any]:
    provider = market_data_provider or EastmoneyMarketDataProvider()
    market_quotes_payload = provider.get_stock_quotes(stock_codes=stock_codes)
    return {
        "market_quotes": market_quotes_payload,
        "provider_layer": _market_quotes_provider_layer(
            provider=provider,
            market_quotes_payload=market_quotes_payload,
        ),
        "degradation_events": getattr(provider, "degradation_events", []),
    }


def _provider_foundation_with_optional_announcement_layer(
    provider: Any,
    fund_provider_metadata: dict[str, Any],
    degradation_events: list[dict[str, str]],
    announcement_layer: dict[str, Any] | None,
    market_quotes_layer: dict[str, Any] | None,
) -> dict[str, Any]:
    foundation = provider.get_provider_foundation(
        fund_provider_metadata=fund_provider_metadata,
        degradation_events=degradation_events,
    )
    if announcement_layer is None and market_quotes_layer is None:
        return foundation
    layers = foundation["layers"]
    if market_quotes_layer is not None:
        layers = {**layers, "market_quotes": market_quotes_layer}
    if announcement_layer is not None:
        layers = {**layers, "announcements": announcement_layer}
    return build_provider_foundation(
        layers=layers,
        degradation_events=degradation_events,
    )


def _market_quotes_provider_layer(
    provider: Any,
    market_quotes_payload: dict[str, Any],
) -> dict[str, Any]:
    provider_name = str(
        market_quotes_payload.get("provider_name")
        or getattr(provider, "provider_name", "market-data-provider")
    )
    data_quality = str(market_quotes_payload.get("data_quality") or "unavailable")
    return {
        "layer": "market_quotes",
        "provider_name": provider_name,
        "provider_version": str(
            market_quotes_payload.get("provider_version")
            or getattr(provider, "provider_version", market_quotes_payload["version"])
        ),
        "data_quality": data_quality,
        "source_url": market_quotes_payload.get("source_url")
        or getattr(provider, "source_url", None),
        "is_mock": provider_name.startswith("mock") or data_quality == "mock",
        "note": "Optional market quote snapshot for current holdings; V1 does not use quotes for scoring yet.",
    }


def _announcement_provider_layer(
    provider: Any,
    announcements_payload: dict[str, Any],
) -> dict[str, Any]:
    provider_name = str(getattr(provider, "provider_name", "announcement-provider"))
    data_quality = str(announcements_payload.get("data_quality") or "unavailable")
    return {
        "layer": "announcements",
        "provider_name": provider_name,
        "provider_version": str(
            getattr(provider, "provider_version", announcements_payload["version"])
        ),
        "data_quality": data_quality,
        "source_url": getattr(provider, "source_url", CNINFO_ANNOUNCEMENT_QUERY_URL),
        "is_mock": provider_name.startswith("mock") or data_quality == "mock",
        "note": "Optional announcement metadata provider; V1 classifies metadata only and does not parse source PDFs.",
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


def _require_iso_date(value: str, field_name: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date in YYYY-MM-DD format") from exc


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
