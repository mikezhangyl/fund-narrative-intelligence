from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.config import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REVIEWED_REGISTRY_PATH,
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    VERSION_DEFAULTS,
)
from src.modules.evidence.announcements import convert_announcements_to_evidence
from src.modules.fund_analysis.aggregation import aggregate_fund_narratives
from src.modules.fund_analysis.mapping import build_mapping_result
from src.modules.narrative_review.queue import build_candidate_review_queue
from src.modules.report_writer.interpretation import interpret_narrative
from src.modules.report_writer.writer import write_reports
from src.modules.signal_service.derived import (
    ANNOUNCEMENT_DERIVED_SIGNAL_PROVIDER,
    FINANCIAL_METRICS_DERIVED_SIGNAL_PROVIDER,
    MARKET_QUOTE_DERIVED_SIGNAL_PROVIDER,
    NEWS_DERIVED_SIGNAL_PROVIDER,
    VALUATION_DERIVED_SIGNAL_PROVIDER,
    derive_announcement_signal_events,
    derive_financial_metrics_signal_events,
    derive_market_quote_signal_events,
    derive_news_signal_events,
    derive_valuation_signal_events,
)
from src.modules.signal_service.scoring import score_narrative_state
from src.modules.signal_service.trace import build_signal_trace_payload
from src.modules.snapshot_writer.writer import write_json_artifact
from src.modules.valuation.snapshots import (
    build_quote_derived_valuation_snapshots,
    valuation_provider_layer,
)
from src.providers.cninfo import (
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNInfoAnnouncementProvider,
)
from src.providers.eastmoney_financials import EastmoneyFinancialMetricsProvider
from src.providers.eastmoney_market import EastmoneyMarketDataProvider
from src.providers.eastmoney_valuation import EastmoneyValuationProvider
from src.providers.factory import select_data_provider
from src.providers.intelligence import (
    ReviewedNarrativeRegistryProvider,
    ReviewedStockNarrativeMappingProvider,
)
from src.providers.mock import MockDataProvider
from src.providers.news import (
    GOOGLE_NEWS_RSS_PROVIDER,
    GOOGLE_NEWS_RSS_SOURCE_URL,
    GOOGLE_NEWS_RSS_VERSION,
    GoogleNewsRssEvidenceProvider,
)
from src.providers.provenance import build_provider_foundation

NARRATIVE_REGISTRY_MODE_FIXTURE = "fixture"
NARRATIVE_REGISTRY_MODE_REVIEWED = "reviewed"
NARRATIVE_REGISTRY_MODES = {
    NARRATIVE_REGISTRY_MODE_FIXTURE,
    NARRATIVE_REGISTRY_MODE_REVIEWED,
}
STOCK_MAPPING_MODE_FIXTURE = "fixture"
STOCK_MAPPING_MODE_REGISTRY_RULE = "registry-rule"
STOCK_MAPPING_MODE_REVIEWED = "reviewed"
STOCK_MAPPING_MODES = {
    STOCK_MAPPING_MODE_FIXTURE,
    STOCK_MAPPING_MODE_REGISTRY_RULE,
    STOCK_MAPPING_MODE_REVIEWED,
}
BASE_INTELLIGENCE_MODE_FIXTURE = "fixture"
BASE_INTELLIGENCE_MODE_PROVIDER_DERIVED = "provider-derived"
BASE_INTELLIGENCE_MODES = {
    BASE_INTELLIGENCE_MODE_FIXTURE,
    BASE_INTELLIGENCE_MODE_PROVIDER_DERIVED,
}
VALUATION_SOURCE_QUOTE_DERIVED = "quote-derived"
VALUATION_SOURCE_EASTMONEY = "eastmoney"
VALUATION_SNAPSHOT_SOURCES = {
    VALUATION_SOURCE_QUOTE_DERIVED,
    VALUATION_SOURCE_EASTMONEY,
}


def run_pipeline(
    fund_code: str,
    provider_mode: str = "mock",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    include_announcement_evidence: bool = False,
    announcement_start_date: str | None = None,
    announcement_provider: Any | None = None,
    include_market_quotes: bool = False,
    market_data_provider: Any | None = None,
    include_valuation_snapshots: bool = False,
    valuation_snapshot_source: str = VALUATION_SOURCE_QUOTE_DERIVED,
    valuation_provider: Any | None = None,
    include_financial_metrics: bool = False,
    financial_metrics_provider: Any | None = None,
    include_news_evidence: bool = False,
    news_evidence_provider: Any | None = None,
    narrative_registry_mode: str = NARRATIVE_REGISTRY_MODE_FIXTURE,
    narrative_registry_path: str | Path | None = None,
    stock_mapping_mode: str = STOCK_MAPPING_MODE_FIXTURE,
    stock_mappings_path: str | Path | None = None,
    base_intelligence_mode: str = BASE_INTELLIGENCE_MODE_FIXTURE,
) -> dict[str, Any]:
    if not fund_code.isdigit():
        raise ValueError("fund_code must contain digits only")
    if announcement_start_date is not None:
        _require_iso_date(announcement_start_date, "announcement_start_date")
    if narrative_registry_mode not in NARRATIVE_REGISTRY_MODES:
        raise ValueError(
            "narrative_registry_mode must be one of: "
            f"{', '.join(sorted(NARRATIVE_REGISTRY_MODES))}"
        )
    if stock_mapping_mode not in STOCK_MAPPING_MODES:
        raise ValueError(
            "stock_mapping_mode must be one of: "
            f"{', '.join(sorted(STOCK_MAPPING_MODES))}"
        )
    if base_intelligence_mode not in BASE_INTELLIGENCE_MODES:
        raise ValueError(
            "base_intelligence_mode must be one of: "
            f"{', '.join(sorted(BASE_INTELLIGENCE_MODES))}"
        )
    if valuation_snapshot_source not in VALUATION_SNAPSHOT_SOURCES:
        raise ValueError(
            "valuation_snapshot_source must be one of: "
            f"{', '.join(sorted(VALUATION_SNAPSHOT_SOURCES))}"
        )
    if (
        base_intelligence_mode == BASE_INTELLIGENCE_MODE_PROVIDER_DERIVED
        and not include_announcement_evidence
    ):
        raise ValueError(
            "base_intelligence_mode=provider-derived requires "
            "--include-cninfo-announcements"
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    provider_selection = select_data_provider(provider_mode)
    provider = provider_selection.provider
    fund_payload = provider.get_fund_holdings(fund_code)
    registry_result = _narrative_registry_inputs(
        provider=provider,
        narrative_registry_mode=narrative_registry_mode,
        narrative_registry_path=narrative_registry_path,
    )
    registry_payload = registry_result["payload"]
    narrative_registry_layer = registry_result["provider_layer"]
    stock_mapping_result = _stock_mapping_inputs(
        provider=provider,
        stock_mapping_mode=stock_mapping_mode,
        stock_mappings_path=stock_mappings_path,
    )
    all_mappings = stock_mapping_result["mappings"]
    stock_mapping_store_layer = stock_mapping_result["provider_layer"]
    mapping_exclusions_payload = provider.get_mapping_exclusions()
    evidence = _base_evidence_inputs(
        provider=provider,
        base_intelligence_mode=base_intelligence_mode,
    )
    signal_events = _base_signal_inputs(
        provider=provider,
        base_intelligence_mode=base_intelligence_mode,
    )

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
        allow_registry_term_fallback=(
            stock_mapping_mode != STOCK_MAPPING_MODE_REVIEWED
        ),
    )
    stock_mapping_layer = stock_mapping_store_layer or _stock_mapping_provider_layer(
        stock_mapping_mode=stock_mapping_mode,
        mapping_result=mapping_result,
        fund_provider_metadata=fund["provider_metadata"],
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
    derived_signal_events: list[dict[str, Any]] = []
    derived_signal_provider_names: list[str] = []
    derived_signal_data_qualities: list[str] = []
    derived_signals_layer: dict[str, Any] | None = None
    evidence_layer: dict[str, Any] | None = None
    signals_layer: dict[str, Any] | None = None
    news_evidence_payload: dict[str, Any] | None = None
    news_evidence_layer: dict[str, Any] | None = None
    market_quotes_payload: dict[str, Any] | None = None
    market_quotes_layer: dict[str, Any] | None = None
    valuation_snapshots_payload: dict[str, Any] | None = None
    valuation_layer: dict[str, Any] | None = None
    financial_metrics_payload: dict[str, Any] | None = None
    financial_metrics_layer: dict[str, Any] | None = None
    if include_market_quotes:
        market_result = _run_market_quotes(
            stock_codes=[holding["stock_code"] for holding in holdings],
            market_data_provider=market_data_provider,
        )
        market_quotes_payload = market_result["market_quotes"]
        market_quotes_layer = market_result["provider_layer"]
        market_quote_signal_events = derive_market_quote_signal_events(
            market_quotes_payload=market_quotes_payload,
            stock_mappings=selected_mappings,
            as_of_date=as_of_date,
        )
        derived_signal_provider_names.append(MARKET_QUOTE_DERIVED_SIGNAL_PROVIDER)
        derived_signal_data_qualities.append(
            str(market_quotes_payload.get("data_quality") or "unavailable")
        )
        if market_quote_signal_events:
            derived_signal_events = [
                *derived_signal_events,
                *market_quote_signal_events,
            ]
            signal_events = [
                *signal_events,
                *market_quote_signal_events,
            ]
        degradation_events = [
            *degradation_events,
            *market_result["degradation_events"],
        ]
        if (
            include_valuation_snapshots
            and valuation_snapshot_source == VALUATION_SOURCE_QUOTE_DERIVED
        ):
            valuation_snapshots_payload = build_quote_derived_valuation_snapshots(
                market_quotes_payload
            )
            valuation_layer = valuation_provider_layer(valuation_snapshots_payload)
    elif (
        include_valuation_snapshots
        and valuation_snapshot_source == VALUATION_SOURCE_QUOTE_DERIVED
    ):
        raise ValueError("include_valuation_snapshots requires include_market_quotes")
    if (
        include_valuation_snapshots
        and valuation_snapshot_source == VALUATION_SOURCE_EASTMONEY
    ):
        valuation_result = _run_valuation_snapshots(
            stock_codes=[holding["stock_code"] for holding in holdings],
            valuation_provider=valuation_provider,
        )
        valuation_snapshots_payload = valuation_result["valuation_snapshots"]
        valuation_layer = valuation_result["provider_layer"]
        degradation_events = [
            *degradation_events,
            *valuation_result["degradation_events"],
        ]
    if valuation_snapshots_payload is not None:
        valuation_signal_events = derive_valuation_signal_events(
            valuation_snapshots_payload=valuation_snapshots_payload,
            stock_mappings=selected_mappings,
            as_of_date=as_of_date,
        )
        if valuation_signal_events:
            derived_signal_provider_names.append(VALUATION_DERIVED_SIGNAL_PROVIDER)
            derived_signal_data_qualities.append(
                str(valuation_snapshots_payload.get("data_quality") or "unavailable")
            )
            derived_signal_events = [
                *derived_signal_events,
                *valuation_signal_events,
            ]
            signal_events = [
                *signal_events,
                *valuation_signal_events,
            ]
    if include_financial_metrics:
        financial_metrics_result = _run_financial_metrics(
            stock_codes=[holding["stock_code"] for holding in holdings],
            financial_metrics_provider=financial_metrics_provider,
        )
        financial_metrics_payload = financial_metrics_result["financial_metrics"]
        financial_metrics_layer = financial_metrics_result["provider_layer"]
        degradation_events = [
            *degradation_events,
            *financial_metrics_result["degradation_events"],
        ]
        financial_metric_signal_events = derive_financial_metrics_signal_events(
            financial_metrics_payload=financial_metrics_payload,
            stock_mappings=selected_mappings,
            as_of_date=as_of_date,
        )
        if financial_metric_signal_events:
            derived_signal_provider_names.append(FINANCIAL_METRICS_DERIVED_SIGNAL_PROVIDER)
            derived_signal_data_qualities.append(
                str(financial_metrics_payload.get("data_quality") or "unavailable")
            )
            derived_signal_events = [
                *derived_signal_events,
                *financial_metric_signal_events,
            ]
            signal_events = [
                *signal_events,
                *financial_metric_signal_events,
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
        announcement_signal_events = derive_announcement_signal_events(
            announcement_evidence_payload["evidence"]
        )
        if announcement_signal_events:
            derived_signal_provider_names.append(ANNOUNCEMENT_DERIVED_SIGNAL_PROVIDER)
            derived_signal_data_qualities.append(
                str(announcement_evidence_payload.get("data_quality") or "unavailable")
            )
            derived_signal_events = [
                *derived_signal_events,
                *announcement_signal_events,
            ]
            signal_events = [
                *signal_events,
                *announcement_signal_events,
            ]

    exposures = aggregate_fund_narratives(
        holdings=holdings,
        mappings=selected_mappings,
        registry=registry_by_id,
    )
    if include_news_evidence:
        news_narratives = [
            registry_by_id[exposure["narrative_id"]]
            for exposure in exposures[:4]
            if exposure["narrative_id"] in registry_by_id
        ]
        news_result = _run_news_evidence(
            narratives=news_narratives,
            all_narrative_ids=[exposure["narrative_id"] for exposure in exposures],
            as_of_date=as_of_date,
            news_evidence_provider=news_evidence_provider,
        )
        news_evidence_payload = news_result["news_evidence"]
        news_evidence_layer = news_result["provider_layer"]
        degradation_events = [
            *degradation_events,
            *news_result["degradation_events"],
        ]
        evidence = [
            *evidence,
            *news_evidence_payload["evidence"],
        ]
        news_signal_events = derive_news_signal_events(news_evidence_payload["evidence"])
        if news_signal_events:
            derived_signal_provider_names.append(NEWS_DERIVED_SIGNAL_PROVIDER)
            derived_signal_data_qualities.append(
                str(news_evidence_payload.get("data_quality") or "unavailable")
            )
            derived_signal_events = [
                *derived_signal_events,
                *news_signal_events,
            ]
            signal_events = [
                *signal_events,
                *news_signal_events,
            ]

    if derived_signal_provider_names:
        derived_signals_layer = _derived_signals_provider_layer(
            provider_names=derived_signal_provider_names,
            data_qualities=derived_signal_data_qualities,
        )
    if base_intelligence_mode == BASE_INTELLIGENCE_MODE_PROVIDER_DERIVED:
        evidence_layer = _provider_derived_evidence_layer(
            announcement_evidence_payload=announcement_evidence_payload,
            news_evidence_payload=news_evidence_payload,
        )
        signals_layer = _provider_derived_signals_layer(
            provider_names=derived_signal_provider_names,
            data_qualities=derived_signal_data_qualities,
        )

    provider_foundation = _provider_foundation_with_optional_announcement_layer(
        provider=provider,
        fund_provider_metadata=fund["provider_metadata"],
        degradation_events=degradation_events,
        announcement_layer=announcement_layer,
        derived_signals_layer=derived_signals_layer,
        market_quotes_layer=market_quotes_layer,
        valuation_layer=valuation_layer,
        financial_metrics_layer=financial_metrics_layer,
        news_evidence_layer=news_evidence_layer,
        narrative_registry_layer=narrative_registry_layer,
        stock_mapping_layer=stock_mapping_layer,
        evidence_layer=evidence_layer,
        signals_layer=signals_layer,
    )
    effective_data_quality = provider_foundation["effective_data_quality"]
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
        "base_intelligence_mode": base_intelligence_mode,
        "narrative_registry_mode": narrative_registry_mode,
        "stock_mapping_mode": stock_mapping_mode,
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
    if news_evidence_payload is not None:
        raw_payload["news_evidence"] = news_evidence_payload
    if market_quotes_payload is not None:
        raw_payload["market_quotes"] = market_quotes_payload
    if valuation_snapshots_payload is not None:
        raw_payload["valuation_snapshots"] = valuation_snapshots_payload
    if financial_metrics_payload is not None:
        raw_payload["financial_metrics"] = financial_metrics_payload
    if derived_signal_provider_names:
        raw_payload["derived_signal_events"] = derived_signal_events

    scoring_payload = {
        "metadata": metadata,
        "fund": fund,
        "holdings": holdings,
        "primary_narrative": primary_narrative,
        "secondary_narratives": secondary_narratives,
        "all_narratives": narrative_results,
        "provider_foundation": provider_foundation,
        "mapping_coverage": mapping_result["coverage"],
        "base_intelligence_mode": base_intelligence_mode,
        "narrative_registry_mode": narrative_registry_mode,
        "stock_mapping_mode": stock_mapping_mode,
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
    if news_evidence_payload is not None:
        scoring_payload["news_evidence"] = news_evidence_payload
    if market_quotes_payload is not None:
        scoring_payload["market_quotes"] = market_quotes_payload
    if valuation_snapshots_payload is not None:
        scoring_payload["valuation_snapshots"] = valuation_snapshots_payload
    if financial_metrics_payload is not None:
        scoring_payload["financial_metrics"] = financial_metrics_payload
    if derived_signal_provider_names:
        scoring_payload["derived_signal_events"] = derived_signal_events

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
    signal_trace_payload = build_signal_trace_payload(
        fund_code=fund_code,
        as_of_date=as_of_date,
        provider_foundation=provider_foundation,
        narratives=narrative_results,
        signal_events=signal_events,
    )

    raw_path = output_path / f"fund_{fund_code}_raw.json"
    scoring_path = output_path / f"fund_{fund_code}_scoring.json"
    review_queue_path = output_path / f"fund_{fund_code}_review_queue.json"
    source_table_path = output_path / f"fund_{fund_code}_source_table.json"
    signal_trace_path = output_path / f"fund_{fund_code}_signal_trace.json"
    manifest_path = output_path / f"fund_{fund_code}_manifest.json"
    write_json_artifact(raw_payload, raw_path)
    write_json_artifact(scoring_payload, scoring_path)
    write_json_artifact(review_queue_payload, review_queue_path)
    write_json_artifact(signal_trace_payload, signal_trace_path)
    write_json_artifact(
        _source_table_payload(
            fund_code=fund_code,
            as_of_date=as_of_date,
            provider_foundation=provider_foundation,
        ),
        source_table_path,
    )
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
            "source_table": source_table_path,
            "signal_trace": signal_trace_path,
            "markdown": report_paths["markdown"],
            "html": report_paths["html"],
        },
    )
    write_json_artifact(manifest_payload, manifest_path)

    return {
        "raw": raw_path,
        "scoring": scoring_path,
        "review_queue": review_queue_path,
        "source_table": source_table_path,
        "signal_trace": signal_trace_path,
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


def _source_table_payload(
    fund_code: str,
    as_of_date: str,
    provider_foundation: dict[str, Any],
) -> dict[str, Any]:
    layers = list(provider_foundation["layers"].values())
    return {
        "version": "source-table-v1",
        "fund_code": fund_code,
        "as_of_date": as_of_date,
        "provider_foundation": provider_foundation,
        "layers": layers,
        "degradation_events": provider_foundation["degradation_events"],
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


def _run_valuation_snapshots(
    stock_codes: list[str],
    valuation_provider: Any | None,
) -> dict[str, Any]:
    provider = valuation_provider or EastmoneyValuationProvider()
    valuation_snapshots_payload = provider.get_valuation_snapshots(stock_codes=stock_codes)
    return {
        "valuation_snapshots": valuation_snapshots_payload,
        "provider_layer": valuation_provider_layer(valuation_snapshots_payload),
        "degradation_events": getattr(provider, "degradation_events", []),
    }


def _run_financial_metrics(
    stock_codes: list[str],
    financial_metrics_provider: Any | None,
) -> dict[str, Any]:
    provider = financial_metrics_provider or EastmoneyFinancialMetricsProvider()
    financial_metrics_payload = provider.get_financial_metrics(stock_codes=stock_codes)
    return {
        "financial_metrics": financial_metrics_payload,
        "provider_layer": _financial_metrics_provider_layer(
            financial_metrics_payload
        ),
        "degradation_events": getattr(provider, "degradation_events", []),
    }


def _run_news_evidence(
    narratives: list[dict[str, Any]],
    all_narrative_ids: list[str],
    as_of_date: str,
    news_evidence_provider: Any | None,
) -> dict[str, Any]:
    provider = news_evidence_provider or GoogleNewsRssEvidenceProvider()
    degradation_events: list[dict[str, str]] = []
    try:
        news_evidence_payload = provider.get_news_evidence(
            narratives=narratives,
            as_of_date=as_of_date,
        )
        news_evidence_payload = _with_news_query_scope(
            payload=news_evidence_payload,
            queried_narrative_ids=[
                str(narrative.get("narrative_id") or "") for narrative in narratives
            ],
            all_narrative_ids=all_narrative_ids,
        )
    except Exception as exc:
        provider_name = str(getattr(provider, "provider_name", GOOGLE_NEWS_RSS_PROVIDER))
        provider_version = str(
            getattr(provider, "provider_version", GOOGLE_NEWS_RSS_VERSION)
        )
        source_url = str(getattr(provider, "source_url", GOOGLE_NEWS_RSS_SOURCE_URL))
        degradation_events.append(
            {
                "type": "provider_unavailable",
                "provider_name": provider_name,
                "reason": f"News evidence provider failed: {exc}",
            }
        )
        news_evidence_payload = {
            "version": "news-evidence-v1",
            "provider_name": provider_name,
            "provider_version": provider_version,
            "data_quality": "unavailable",
            "source_url": source_url,
            "retrieved_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "query_scope": _news_query_scope(
                queried_narrative_ids=[
                    str(narrative.get("narrative_id") or "") for narrative in narratives
                ],
                all_narrative_ids=all_narrative_ids,
            ),
            "evidence": [],
            "missing_narrative_ids": sorted(
                str(narrative.get("narrative_id"))
                for narrative in narratives
                if narrative.get("narrative_id")
            ),
            "skipped_item_count": 0,
            "degradation_events": degradation_events,
        }
    else:
        degradation_events = [
            *degradation_events,
            *news_evidence_payload.get("degradation_events", []),
        ]
    degradation_events = [*degradation_events, *getattr(provider, "degradation_events", [])]
    return {
        "news_evidence": news_evidence_payload,
        "provider_layer": _news_evidence_provider_layer(
            provider=provider,
            news_evidence_payload=news_evidence_payload,
        ),
        "degradation_events": degradation_events,
    }


def _provider_foundation_with_optional_announcement_layer(
    provider: Any,
    fund_provider_metadata: dict[str, Any],
    degradation_events: list[dict[str, str]],
    announcement_layer: dict[str, Any] | None,
    derived_signals_layer: dict[str, Any] | None,
    market_quotes_layer: dict[str, Any] | None,
    valuation_layer: dict[str, Any] | None,
    financial_metrics_layer: dict[str, Any] | None,
    news_evidence_layer: dict[str, Any] | None,
    narrative_registry_layer: dict[str, Any] | None,
    stock_mapping_layer: dict[str, Any] | None,
    evidence_layer: dict[str, Any] | None,
    signals_layer: dict[str, Any] | None,
) -> dict[str, Any]:
    foundation = provider.get_provider_foundation(
        fund_provider_metadata=fund_provider_metadata,
        degradation_events=degradation_events,
    )
    if (
        announcement_layer is None
        and derived_signals_layer is None
        and market_quotes_layer is None
        and valuation_layer is None
        and financial_metrics_layer is None
        and news_evidence_layer is None
        and narrative_registry_layer is None
        and stock_mapping_layer is None
        and evidence_layer is None
        and signals_layer is None
    ):
        return foundation
    layers = foundation["layers"]
    if evidence_layer is not None:
        layers = {**layers, "evidence": evidence_layer}
    if signals_layer is not None:
        layers = {**layers, "signals": signals_layer}
    if narrative_registry_layer is not None:
        layers = {**layers, "narrative_registry": narrative_registry_layer}
    if stock_mapping_layer is not None:
        layers = {**layers, "stock_mappings": stock_mapping_layer}
    if market_quotes_layer is not None:
        layers = {**layers, "market_quotes": market_quotes_layer}
    if valuation_layer is not None:
        layers = {**layers, "valuation": valuation_layer}
    if financial_metrics_layer is not None:
        layers = {**layers, "financial_metrics": financial_metrics_layer}
    if news_evidence_layer is not None:
        layers = {**layers, "news_evidence": news_evidence_layer}
    if announcement_layer is not None:
        layers = {**layers, "announcements": announcement_layer}
    if derived_signals_layer is not None:
        layers = {**layers, "derived_signals": derived_signals_layer}
    return build_provider_foundation(
        layers=layers,
        degradation_events=degradation_events,
    )


def _narrative_registry_inputs(
    provider: Any,
    narrative_registry_mode: str,
    narrative_registry_path: str | Path | None,
) -> dict[str, Any]:
    if narrative_registry_mode == NARRATIVE_REGISTRY_MODE_FIXTURE:
        return {
            "payload": provider.get_narrative_registry(),
            "provider_layer": None,
        }
    if narrative_registry_mode == NARRATIVE_REGISTRY_MODE_REVIEWED:
        registry_provider = ReviewedNarrativeRegistryProvider(
            registry_path=Path(narrative_registry_path)
            if narrative_registry_path
            else DEFAULT_REVIEWED_REGISTRY_PATH
        )
        return {
            "payload": registry_provider.get_narrative_registry(),
            "provider_layer": registry_provider.get_provider_layer(),
        }
    raise ValueError(
        "narrative_registry_mode must be one of: "
        f"{', '.join(sorted(NARRATIVE_REGISTRY_MODES))}"
    )


def _base_evidence_inputs(provider: Any, base_intelligence_mode: str) -> list[dict[str, Any]]:
    if base_intelligence_mode == BASE_INTELLIGENCE_MODE_FIXTURE:
        return provider.get_evidence()
    if base_intelligence_mode == BASE_INTELLIGENCE_MODE_PROVIDER_DERIVED:
        return []
    raise ValueError(
        "base_intelligence_mode must be one of: "
        f"{', '.join(sorted(BASE_INTELLIGENCE_MODES))}"
    )


def _base_signal_inputs(provider: Any, base_intelligence_mode: str) -> list[dict[str, Any]]:
    if base_intelligence_mode == BASE_INTELLIGENCE_MODE_FIXTURE:
        return provider.get_signal_events()
    if base_intelligence_mode == BASE_INTELLIGENCE_MODE_PROVIDER_DERIVED:
        return []
    raise ValueError(
        "base_intelligence_mode must be one of: "
        f"{', '.join(sorted(BASE_INTELLIGENCE_MODES))}"
    )


def _stock_mapping_inputs(
    provider: Any,
    stock_mapping_mode: str,
    stock_mappings_path: str | Path | None,
) -> dict[str, Any]:
    if stock_mapping_mode == STOCK_MAPPING_MODE_FIXTURE:
        return {
            "mappings": provider.get_stock_narrative_mappings(),
            "provider_layer": None,
        }
    if stock_mapping_mode == STOCK_MAPPING_MODE_REGISTRY_RULE:
        return {"mappings": [], "provider_layer": None}
    if stock_mapping_mode == STOCK_MAPPING_MODE_REVIEWED:
        mapping_provider = ReviewedStockNarrativeMappingProvider(
            mappings_path=Path(stock_mappings_path)
            if stock_mappings_path
            else DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH
        )
        return {
            "mappings": mapping_provider.get_stock_narrative_mappings(),
            "provider_layer": mapping_provider.get_provider_layer(),
        }
    raise ValueError(
        "stock_mapping_mode must be one of: "
        f"{', '.join(sorted(STOCK_MAPPING_MODES))}"
    )


def _stock_mapping_provider_layer(
    stock_mapping_mode: str,
    mapping_result: dict[str, Any],
    fund_provider_metadata: dict[str, Any],
) -> dict[str, Any] | None:
    if stock_mapping_mode == STOCK_MAPPING_MODE_FIXTURE:
        return None
    coverage = mapping_result["coverage"]
    covered = coverage["covered_holding_count"]
    total = coverage["total_holding_count"]
    review_count = len(mapping_result["mapping_precision_flags"])
    input_data_quality = str(fund_provider_metadata.get("data_quality") or "unavailable")
    data_quality = "mock" if input_data_quality == "mock" else "partial"
    is_mock = data_quality == "mock"
    return {
        "layer": "stock_mappings",
        "provider_name": "registry-rule-stock-mapping",
        "provider_version": "stock-mapping-v1",
        "data_quality": data_quality,
        "source_url": (
            "mock://derived/registry-term-rule-stock-mapping"
            if is_mock
            else "derived://registry-term-rule-stock-mapping"
        ),
        "is_mock": is_mock,
        "note": (
            "Runtime stock-to-narrative mappings derived from current holdings "
            f"and Narrative Registry terms; coverage {covered}/{total}, "
            f"review flags {review_count}. Registry provenance is disclosed "
            "separately."
        ),
    }


def _provider_derived_evidence_layer(
    announcement_evidence_payload: dict[str, Any] | None,
    news_evidence_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    data_qualities = [
        str(payload.get("data_quality") or "unavailable")
        for payload in (announcement_evidence_payload, news_evidence_payload)
        if payload is not None and payload.get("evidence")
    ]
    data_quality = _derived_signal_data_quality(data_qualities)
    evidence_count = sum(
        len(payload.get("evidence") or [])
        for payload in (announcement_evidence_payload, news_evidence_payload)
        if payload is not None
    )
    source_names = []
    if announcement_evidence_payload is not None and announcement_evidence_payload.get(
        "evidence"
    ):
        source_names.append("announcement_evidence")
    if news_evidence_payload is not None and news_evidence_payload.get("evidence"):
        source_names.append("news_evidence")
    source_summary = ", ".join(source_names) if source_names else "none"
    return {
        "layer": "evidence",
        "provider_name": "provider-derived-evidence",
        "provider_version": "provider-derived-evidence-v1",
        "data_quality": data_quality,
        "source_url": "derived://provider-evidence",
        "is_mock": False,
        "note": (
            "Evidence input excludes base fixtures and uses provider-derived "
            f"evidence records only; sources: {source_summary}; "
            f"evidence count {evidence_count}."
        ),
    }


def _provider_derived_signals_layer(
    provider_names: list[str],
    data_qualities: list[str],
) -> dict[str, Any]:
    data_quality = _derived_signal_data_quality(data_qualities)
    source_summary = ", ".join(sorted(set(provider_names))) if provider_names else "none"
    return {
        "layer": "signals",
        "provider_name": "provider-derived-signals",
        "provider_version": "provider-derived-signals-v1",
        "data_quality": data_quality,
        "source_url": "derived://provider-signals",
        "is_mock": False,
        "note": (
            "Signal input excludes base fixtures and uses provider-derived "
            f"signal events only; source providers: {source_summary}."
        ),
    }


def _derived_signals_provider_layer(
    provider_names: list[str],
    data_qualities: list[str],
) -> dict[str, Any]:
    provider_name = _derived_signal_provider_name(provider_names)
    return {
        "layer": "derived_signals",
        "provider_name": provider_name,
        "provider_version": "derived-signals-v1",
        "data_quality": _derived_signal_data_quality(data_qualities),
        "source_url": f"derived://{provider_name}",
        "is_mock": False,
        "note": (
            "Derived from real provider evidence, news evidence, quote snapshots, "
            "or valuation snapshots; V1 keeps base fixture signals separately."
        ),
    }


def _derived_signal_provider_name(provider_names: list[str]) -> str:
    providers = sorted(set(provider_names))
    if len(providers) == 1:
        return providers[0]
    return "mixed-derived-signals"


def _derived_signal_data_quality(data_qualities: list[str]) -> str:
    qualities = [quality for quality in data_qualities if quality != "unavailable"]
    if not qualities:
        return "unavailable"
    if all(quality == "fresh" for quality in qualities):
        return "fresh"
    return "partial"


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


def _financial_metrics_provider_layer(
    financial_metrics_payload: dict[str, Any],
) -> dict[str, Any]:
    provider_name = str(
        financial_metrics_payload.get("provider_name")
        or "financial-metrics-provider"
    )
    data_quality = str(financial_metrics_payload.get("data_quality") or "unavailable")
    return {
        "layer": "financial_metrics",
        "provider_name": provider_name,
        "provider_version": str(
            financial_metrics_payload.get("provider_version")
            or financial_metrics_payload["version"]
        ),
        "data_quality": data_quality,
        "source_url": financial_metrics_payload.get("source_url"),
        "is_mock": provider_name.startswith("mock") or data_quality == "mock",
        "note": (
            "Optional financial metrics provider; V1 uses latest reported "
            "revenue/profit growth metrics as deterministic earnings signals."
        ),
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


def _news_evidence_provider_layer(
    provider: Any,
    news_evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    provider_name = str(
        news_evidence_payload.get("provider_name")
        or getattr(provider, "provider_name", "news-evidence-provider")
    )
    data_quality = str(news_evidence_payload.get("data_quality") or "unavailable")
    evidence_count = len(news_evidence_payload.get("evidence") or [])
    query_scope = news_evidence_payload.get("query_scope")
    if not isinstance(query_scope, dict):
        query_scope = {
            "requested_narrative_ids": [],
            "queried_narrative_ids": [],
        }
    return {
        "layer": "news_evidence",
        "provider_name": provider_name,
        "provider_version": str(
            news_evidence_payload.get("provider_version")
            or getattr(provider, "provider_version", news_evidence_payload["version"])
        ),
        "data_quality": data_quality,
        "source_url": news_evidence_payload.get("source_url")
        or getattr(provider, "source_url", GOOGLE_NEWS_RSS_SOURCE_URL),
        "is_mock": provider_name.startswith("mock") or data_quality == "mock",
        "note": (
            "Optional news evidence provider; V1 classifies RSS titles/snippets "
            "only, does not parse article bodies, "
            f"queried {len(query_scope.get('queried_narrative_ids', []))}/"
            f"{len(query_scope.get('requested_narrative_ids', []))} mapped narratives, "
            f"evidence count {evidence_count}."
        ),
    }


def _with_news_query_scope(
    payload: dict[str, Any],
    queried_narrative_ids: list[str],
    all_narrative_ids: list[str],
) -> dict[str, Any]:
    existing_scope = payload.get("query_scope")
    if isinstance(existing_scope, dict):
        queried = existing_scope.get("queried_narrative_ids")
        if isinstance(queried, list):
            queried_narrative_ids = [str(item) for item in queried]
    return {
        **payload,
        "query_scope": _news_query_scope(
            queried_narrative_ids=queried_narrative_ids,
            all_narrative_ids=all_narrative_ids,
        ),
    }


def _news_query_scope(
    queried_narrative_ids: list[str],
    all_narrative_ids: list[str],
) -> dict[str, Any]:
    requested = sorted(narrative_id for narrative_id in set(all_narrative_ids) if narrative_id)
    queried = sorted(narrative_id for narrative_id in set(queried_narrative_ids) if narrative_id)
    return {
        "requested_narrative_ids": requested,
        "queried_narrative_ids": queried,
        "omitted_narrative_ids": sorted(set(requested) - set(queried)),
        "query_limit": 4,
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
