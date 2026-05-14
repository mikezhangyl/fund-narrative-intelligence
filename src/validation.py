from __future__ import annotations

from typing import Any

from src.errors import ProviderContractError

FUND_REQUIRED_FIELDS = {
    "fund_code",
    "fund_name",
    "fund_type",
    "currency",
    "provider_metadata",
}

PROVIDER_METADATA_REQUIRED_FIELDS = {
    "provider_name",
    "provider_version",
    "source_url",
    "as_of_date",
    "retrieved_at",
    "data_quality",
    "confidence_multiplier",
}

HOLDING_REQUIRED_FIELDS = {"stock_code", "stock_name", "weight"}


def validate_fund_payload(payload: dict[str, Any], fund_code: str) -> None:
    _require_mapping(payload, "fund payload")
    _require_keys(payload, {"as_of_date", "fund", "holdings"}, "fund payload")

    fund = payload["fund"]
    _require_mapping(fund, "fund")
    _require_keys(fund, FUND_REQUIRED_FIELDS, "fund")

    if fund["fund_code"] != fund_code:
        raise ProviderContractError(
            f"fund.fund_code must match requested fund code {fund_code}"
        )

    provider_metadata = fund["provider_metadata"]
    _require_mapping(provider_metadata, "provider_metadata")
    _require_keys(
        provider_metadata, PROVIDER_METADATA_REQUIRED_FIELDS, "provider_metadata"
    )

    holdings = payload["holdings"]
    if not isinstance(holdings, list) or not holdings:
        raise ProviderContractError("holdings must be a non-empty list")

    for index, holding in enumerate(holdings):
        context = f"holdings[{index}]"
        _require_mapping(holding, context)
        _require_keys(holding, HOLDING_REQUIRED_FIELDS, context)
        weight = holding["weight"]
        if not isinstance(weight, int | float):
            raise ProviderContractError(f"{context}.weight must be numeric")
        if weight <= 0 or weight > 1:
            raise ProviderContractError(f"{context}.weight must be within (0, 1]")


def validate_registry_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "narrative registry")
    _require_keys(payload, {"version", "narratives"}, "narrative registry")
    if not isinstance(payload["narratives"], list) or not payload["narratives"]:
        raise ProviderContractError("narratives must be a non-empty list")
    for index, narrative in enumerate(payload["narratives"]):
        context = f"narratives[{index}]"
        _require_mapping(narrative, context)
        _require_keys(
            narrative,
            {
                "narrative_id",
                "canonical_taxonomy",
                "name",
                "parent_id",
                "level",
                "status",
                "aliases",
                "related_terms",
                "human_review_status",
            },
            context,
        )


def validate_mapping_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "stock narrative mappings")
    _require_keys(payload, {"version", "mappings"}, "stock narrative mappings")
    if not isinstance(payload["mappings"], list):
        raise ProviderContractError("mappings must be a list")
    for index, mapping in enumerate(payload["mappings"]):
        context = f"mappings[{index}]"
        _require_mapping(mapping, context)
        _require_keys(
            mapping,
            {"stock_code", "narrative_id", "mapping_weight", "confidence", "method"},
            context,
        )
        _require_probability(mapping["mapping_weight"], f"{context}.mapping_weight")
        _require_probability(mapping["confidence"], f"{context}.confidence")


def validate_mapping_exclusion_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "mapping exclusions")
    _require_keys(payload, {"version", "exclusions"}, "mapping exclusions")
    if not isinstance(payload["exclusions"], list):
        raise ProviderContractError("exclusions must be a list")
    for index, exclusion in enumerate(payload["exclusions"]):
        context = f"exclusions[{index}]"
        _require_mapping(exclusion, context)
        _require_keys(
            exclusion,
            {
                "exclusion_id",
                "stock_code",
                "narrative_id",
                "method",
                "reason",
                "recommended_action",
            },
            context,
        )


def validate_evidence_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "evidence")
    _require_keys(payload, {"version", "evidence"}, "evidence")
    if not isinstance(payload["evidence"], list):
        raise ProviderContractError("evidence must be a list")
    for index, item in enumerate(payload["evidence"]):
        context = f"evidence[{index}]"
        _require_mapping(item, context)
        _require_keys(
            item,
            {
                "evidence_id",
                "narrative_id",
                "type",
                "source",
                "source_url",
                "title",
                "summary",
                "sentiment",
                "confidence",
                "event_date",
            },
            context,
        )
        _require_probability(item["confidence"], f"{context}.confidence")


def validate_signal_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "signal events")
    _require_keys(payload, {"version", "signal_events"}, "signal events")
    if not isinstance(payload["signal_events"], list):
        raise ProviderContractError("signal_events must be a list")
    for index, item in enumerate(payload["signal_events"]):
        context = f"signal_events[{index}]"
        _require_mapping(item, context)
        _require_keys(
            item,
            {
                "signal_id",
                "narrative_id",
                "signal_type",
                "strength",
                "confidence",
                "confidence_multiplier",
                "event_date",
                "half_life_days",
            },
            context,
        )
        _require_probability(item["strength"], f"{context}.strength")
        _require_probability(item["confidence"], f"{context}.confidence")
        _require_probability(
            item["confidence_multiplier"], f"{context}.confidence_multiplier"
        )
        if item["half_life_days"] <= 0:
            raise ProviderContractError(f"{context}.half_life_days must be positive")


def _require_mapping(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise ProviderContractError(f"{context} must be an object")


def _require_keys(value: dict[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ProviderContractError(f"{context} missing required fields: {missing}")


def _require_probability(value: Any, context: str) -> None:
    if not isinstance(value, int | float):
        raise ProviderContractError(f"{context} must be numeric")
    if value < 0 or value > 1:
        raise ProviderContractError(f"{context} must be within [0, 1]")
