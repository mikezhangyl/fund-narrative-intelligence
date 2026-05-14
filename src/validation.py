from __future__ import annotations

from pathlib import Path
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

SOURCE_TABLE_LAYER_REQUIRED_FIELDS = {
    "layer",
    "display_name",
    "provider_name",
    "provider_version",
    "data_quality",
    "source_url",
    "is_mock",
}

SOURCE_TABLE_LAYER_DATA_QUALITIES = {"fresh", "partial", "mock", "unavailable"}


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
    candidate_narratives = payload.get("candidate_narratives", [])
    if not isinstance(candidate_narratives, list):
        raise ProviderContractError("candidate_narratives must be a list")
    for index, candidate in enumerate(candidate_narratives):
        _validate_candidate_narrative(candidate, f"candidate_narratives[{index}]")


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


def validate_market_quote_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "market quotes")
    _require_keys(
        payload,
        {
            "version",
            "provider_name",
            "provider_version",
            "data_quality",
            "source_url",
            "retrieved_at",
            "quotes",
            "missing_stock_codes",
        },
        "market quotes",
    )
    if payload["data_quality"] not in {"fresh", "partial", "unavailable"}:
        raise ProviderContractError(
            "market quotes data_quality must be fresh, partial, or unavailable"
        )
    if not isinstance(payload["quotes"], list):
        raise ProviderContractError("market quotes quotes must be a list")
    if not isinstance(payload["missing_stock_codes"], list):
        raise ProviderContractError("market quotes missing_stock_codes must be a list")
    for index, quote in enumerate(payload["quotes"]):
        context = f"quotes[{index}]"
        _require_mapping(quote, context)
        _require_keys(
            quote,
            {
                "stock_code",
                "stock_name",
                "latest_price",
                "change_percent",
                "change_amount",
                "volume",
                "amount",
                "high",
                "low",
                "open",
                "previous_close",
                "retrieved_at",
            },
            context,
        )
        if not quote["stock_code"]:
            raise ProviderContractError(f"{context}.stock_code must be non-empty")


def validate_valuation_snapshot_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "valuation snapshots")
    _require_keys(
        payload,
        {
            "version",
            "provider_name",
            "provider_version",
            "data_quality",
            "source_url",
            "retrieved_at",
            "valuation_basis",
            "valuations",
            "missing_stock_codes",
        },
        "valuation snapshots",
    )
    if payload["version"] != "valuation-snapshot-v1":
        raise ProviderContractError("valuation snapshots version is unsupported")
    if payload["provider_name"] != "quote-derived-valuation":
        raise ProviderContractError(
            "valuation snapshots provider_name must be quote-derived-valuation"
        )
    if payload["provider_version"] != "quote-derived-valuation-v1":
        raise ProviderContractError(
            "valuation snapshots provider_version must be quote-derived-valuation-v1"
        )
    if payload["valuation_basis"] != "quote_derived_context":
        raise ProviderContractError("valuation snapshots valuation_basis is unsupported")
    if payload["data_quality"] not in {"fresh", "partial", "mock", "unavailable"}:
        raise ProviderContractError(
            "valuation snapshots data_quality must be fresh, partial, mock, or unavailable"
        )
    for field in {"provider_name", "provider_version", "source_url", "retrieved_at"}:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ProviderContractError(
                f"valuation snapshots {field} must be a non-empty string"
            )
    if not isinstance(payload["valuations"], list):
        raise ProviderContractError("valuation snapshots valuations must be a list")
    if not isinstance(payload["missing_stock_codes"], list):
        raise ProviderContractError(
            "valuation snapshots missing_stock_codes must be a list"
        )
    for index, valuation in enumerate(payload["valuations"]):
        _validate_valuation_snapshot_item(valuation, f"valuations[{index}]")


def _validate_valuation_snapshot_item(item: Any, context: str) -> None:
    _require_mapping(item, context)
    _require_keys(
        item,
        {
            "stock_code",
            "stock_name",
            "latest_price",
            "previous_close",
            "price_change_percent",
            "valuation_pressure",
            "source",
            "source_provider",
            "source_url",
            "retrieved_at",
        },
        context,
    )
    if not item["stock_code"]:
        raise ProviderContractError(f"{context}.stock_code must be non-empty")
    if item["valuation_pressure"] not in {"elevated", "neutral", "discounted", "unknown"}:
        raise ProviderContractError(f"{context}.valuation_pressure is unsupported")
    if item["source"] != "market_quote":
        raise ProviderContractError(f"{context}.source must be market_quote")
    for field in {"source_provider", "source_url", "retrieved_at"}:
        if not isinstance(item[field], str) or not item[field]:
            raise ProviderContractError(f"{context}.{field} must be a non-empty string")


def validate_news_evidence_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "news evidence")
    _require_keys(
        payload,
        {
            "version",
            "provider_name",
            "provider_version",
            "data_quality",
            "source_url",
            "retrieved_at",
            "query_scope",
            "evidence",
            "missing_narrative_ids",
            "skipped_item_count",
            "degradation_events",
        },
        "news evidence",
    )
    if payload["version"] != "news-evidence-v1":
        raise ProviderContractError("news evidence version is unsupported")
    if payload["data_quality"] not in {"fresh", "partial", "mock", "unavailable"}:
        raise ProviderContractError(
            "news evidence data_quality must be fresh, partial, mock, or unavailable"
        )
    for field in {"provider_name", "provider_version", "source_url", "retrieved_at"}:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ProviderContractError(f"news evidence {field} must be a non-empty string")
    if not isinstance(payload["evidence"], list):
        raise ProviderContractError("news evidence evidence must be a list")
    _validate_news_query_scope(payload["query_scope"])
    if not isinstance(payload["missing_narrative_ids"], list):
        raise ProviderContractError(
            "news evidence missing_narrative_ids must be a list"
        )
    if not isinstance(payload["skipped_item_count"], int):
        raise ProviderContractError("news evidence skipped_item_count must be an integer")
    if not isinstance(payload["degradation_events"], list):
        raise ProviderContractError("news evidence degradation_events must be a list")
    validate_evidence_payload(
        {"version": payload["version"], "evidence": payload["evidence"]}
    )
    for index, item in enumerate(payload["evidence"]):
        context = f"news evidence evidence[{index}]"
        for field in {"source_provider", "retrieved_at", "provider_data_quality"}:
            if not isinstance(item.get(field), str) or not item[field]:
                raise ProviderContractError(f"{context}.{field} must be non-empty")


def _validate_news_query_scope(query_scope: Any) -> None:
    _require_mapping(query_scope, "news evidence query_scope")
    _require_keys(
        query_scope,
        {
            "requested_narrative_ids",
            "queried_narrative_ids",
            "omitted_narrative_ids",
            "query_limit",
        },
        "news evidence query_scope",
    )
    for field in {
        "requested_narrative_ids",
        "queried_narrative_ids",
        "omitted_narrative_ids",
    }:
        if not isinstance(query_scope[field], list):
            raise ProviderContractError(f"news evidence query_scope.{field} must be a list")
    if not isinstance(query_scope["query_limit"], int) or query_scope["query_limit"] < 0:
        raise ProviderContractError(
            "news evidence query_scope.query_limit must be a non-negative integer"
        )


def validate_review_action_preview_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "review action preview")
    _require_keys(
        payload,
        {
            "version",
            "status",
            "source_registry_mutated",
            "action",
            "summary",
            "registry_delta",
            "result_registry",
        },
        "review action preview",
    )
    if payload["version"] != "candidate-review-action-preview-v1":
        raise ProviderContractError("review action preview version is unsupported")
    if payload["status"] != "previewed":
        raise ProviderContractError("review action preview status must be previewed")
    if not isinstance(payload["source_registry_mutated"], bool):
        raise ProviderContractError("source_registry_mutated must be boolean")
    _require_mapping(payload["action"], "review action preview action")
    _validate_review_action_preview_summary(payload["summary"])
    _validate_review_action_registry_delta(payload["registry_delta"])
    validate_registry_payload(payload["result_registry"])


def validate_review_action_persistence_result_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "review action persistence result")
    _require_keys(
        payload,
        {
            "version",
            "status",
            "action_id",
            "candidate_narrative_id",
            "registry_path",
            "registry_output_path",
            "registry_overwritten",
            "overwrite_policy",
            "registry_delta",
            "persistence_result_path",
        },
        "review action persistence result",
    )
    if payload["version"] != "review-action-persistence-result-v1":
        raise ProviderContractError(
            "review action persistence result version is unsupported"
        )
    if payload["status"] != "persisted":
        raise ProviderContractError(
            "review action persistence result status must be persisted"
        )
    for field in {
        "action_id",
        "candidate_narrative_id",
        "registry_path",
        "registry_output_path",
        "persistence_result_path",
    }:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ProviderContractError(
                f"review action persistence result {field} must be a non-empty string"
            )
    if not isinstance(payload["registry_overwritten"], bool):
        raise ProviderContractError(
            "review action persistence result registry_overwritten must be boolean"
        )
    _validate_review_action_persistence_overwrite_policy(
        payload["overwrite_policy"]
    )
    _validate_review_action_registry_delta(payload["registry_delta"])


def validate_review_queue_artifact_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "review queue artifact")
    _require_keys(
        payload,
        {
            "metadata",
            "fund",
            "provider_foundation",
            "candidate_review_queue",
            "candidate_narratives",
            "excluded_mapping_candidates",
        },
        "review queue artifact",
    )
    _require_mapping(payload["metadata"], "review queue artifact metadata")
    _require_mapping(payload["fund"], "review queue artifact fund")
    _require_mapping(
        payload["provider_foundation"],
        "review queue artifact provider_foundation",
    )

    candidate_narratives = payload["candidate_narratives"]
    if not isinstance(candidate_narratives, list):
        raise ProviderContractError("candidate_narratives must be a list")
    candidate_ids = set()
    for index, candidate in enumerate(candidate_narratives):
        candidate_id = _validate_candidate_narrative(
            candidate,
            f"candidate_narratives[{index}]",
        )
        if candidate_id in candidate_ids:
            raise ProviderContractError(
                f"candidate_narratives[{index}].candidate_narrative_id must be unique"
            )
        candidate_ids.add(candidate_id)

    excluded_mapping_candidates = payload["excluded_mapping_candidates"]
    if not isinstance(excluded_mapping_candidates, list):
        raise ProviderContractError("excluded_mapping_candidates must be a list")
    for index, exclusion in enumerate(excluded_mapping_candidates):
        _validate_review_queue_exclusion(
            exclusion,
            f"excluded_mapping_candidates[{index}]",
        )

    _validate_candidate_review_queue(
        payload["candidate_review_queue"],
        candidate_ids,
    )


def validate_pipeline_artifact_manifest_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "pipeline artifact manifest")
    _require_keys(
        payload,
        {
            "version",
            "fund_code",
            "as_of_date",
            "provider_mode",
            "data_quality",
            "web_ready",
            "provider_foundation",
            "degradation_events",
            "artifacts",
        },
        "pipeline artifact manifest",
    )
    if payload["version"] != "pipeline-artifact-manifest-v1":
        raise ProviderContractError("pipeline artifact manifest version is unsupported")
    for field in {"fund_code", "as_of_date", "provider_mode", "data_quality"}:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ProviderContractError(
                f"pipeline artifact manifest {field} must be a non-empty string"
            )
    if not isinstance(payload["web_ready"], bool):
        raise ProviderContractError("pipeline artifact manifest web_ready must be boolean")
    _require_mapping(
        payload["provider_foundation"],
        "pipeline artifact manifest provider_foundation",
    )
    if not isinstance(payload["degradation_events"], list):
        raise ProviderContractError(
            "pipeline artifact manifest degradation_events must be a list"
        )
    _validate_pipeline_manifest_artifacts(payload["artifacts"])


def validate_source_table_artifact_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "source table artifact")
    _require_keys(
        payload,
        {
            "version",
            "fund_code",
            "as_of_date",
            "provider_foundation",
            "layers",
            "degradation_events",
        },
        "source table artifact",
    )
    if payload["version"] != "source-table-v1":
        raise ProviderContractError("source table artifact version is unsupported")
    for field in {"fund_code", "as_of_date"}:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ProviderContractError(
                f"source table artifact {field} must be a non-empty string"
            )
    _require_mapping(payload["provider_foundation"], "source table provider_foundation")
    if not isinstance(payload["layers"], list) or not payload["layers"]:
        raise ProviderContractError("source table layers must be a non-empty list")
    if not isinstance(payload["degradation_events"], list):
        raise ProviderContractError("source table degradation_events must be a list")
    foundation_layers = payload["provider_foundation"].get("layers")
    _require_mapping(foundation_layers, "source table provider_foundation.layers")
    expected_layers = _layers_by_name(list(foundation_layers.values()))
    if _layers_by_name(payload["layers"]) != expected_layers:
        raise ProviderContractError("source table layers must match provider_foundation")
    if payload["degradation_events"] != payload["provider_foundation"].get(
        "degradation_events"
    ):
        raise ProviderContractError(
            "source table degradation_events must match provider_foundation"
        )


def validate_workspace_snapshot_payload(payload: dict[str, Any]) -> None:
    _require_mapping(payload, "workspace snapshot")
    _require_keys(
        payload,
        {
            "version",
            "fund_code",
            "as_of_date",
            "provider_mode",
            "data_quality",
            "web_ready",
            "artifact_manifest",
            "provider_foundation",
            "source_table",
            "review_queue",
            "narratives",
            "reports",
            "approval_workflow",
        },
        "workspace snapshot",
    )
    if payload["version"] != "workspace-snapshot-v1":
        raise ProviderContractError("workspace snapshot version is unsupported")
    for field in {"fund_code", "as_of_date", "provider_mode", "data_quality"}:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ProviderContractError(
                f"workspace snapshot {field} must be a non-empty string"
            )
    if payload["web_ready"] is not True:
        raise ProviderContractError("workspace snapshot web_ready must be true")
    validate_pipeline_artifact_manifest_payload(payload["artifact_manifest"])
    validate_source_table_artifact_payload(payload["source_table"])
    validate_review_queue_artifact_payload(payload["review_queue"])
    _require_mapping(payload["provider_foundation"], "workspace snapshot provider_foundation")
    _validate_workspace_snapshot_identity(payload)
    _validate_workspace_snapshot_narratives(payload["narratives"])
    _validate_workspace_snapshot_reports(payload["reports"])
    _validate_workspace_snapshot_approval_workflow(payload["approval_workflow"])


def _validate_workspace_snapshot_identity(payload: dict[str, Any]) -> None:
    manifest = payload["artifact_manifest"]
    if payload["fund_code"] != manifest["fund_code"]:
        raise ProviderContractError("workspace snapshot fund_code mismatch")
    if payload["as_of_date"] != manifest["as_of_date"]:
        raise ProviderContractError("workspace snapshot as_of_date mismatch")
    if payload["provider_mode"] != manifest["provider_mode"]:
        raise ProviderContractError("workspace snapshot provider_mode mismatch")
    if payload["data_quality"] != manifest["data_quality"]:
        raise ProviderContractError("workspace snapshot data_quality mismatch")
    if payload["provider_foundation"] != manifest["provider_foundation"]:
        raise ProviderContractError("workspace snapshot provider_foundation mismatch")
    if payload["source_table"]["fund_code"] != payload["fund_code"]:
        raise ProviderContractError("workspace snapshot source table fund_code mismatch")
    if payload["source_table"]["as_of_date"] != payload["as_of_date"]:
        raise ProviderContractError(
            "workspace snapshot source table as_of_date mismatch"
        )
    if payload["source_table"]["provider_foundation"] != payload["provider_foundation"]:
        raise ProviderContractError(
            "workspace snapshot source table provider_foundation mismatch"
        )
    if payload["review_queue"]["provider_foundation"] != payload["provider_foundation"]:
        raise ProviderContractError(
            "workspace snapshot review queue provider_foundation mismatch"
        )
    queue_metadata = payload["review_queue"].get("metadata", {})
    if queue_metadata.get("fund_code") != payload["fund_code"]:
        raise ProviderContractError("workspace snapshot review queue fund_code mismatch")
    if queue_metadata.get("as_of_date") != payload["as_of_date"]:
        raise ProviderContractError("workspace snapshot review queue as_of_date mismatch")
    if queue_metadata.get("data_quality") != payload["data_quality"]:
        raise ProviderContractError("workspace snapshot review queue data_quality mismatch")
    if payload["review_queue"].get("fund", {}).get("fund_code") != payload["fund_code"]:
        raise ProviderContractError("workspace snapshot review queue fund_code mismatch")


def _validate_workspace_snapshot_narratives(narratives: Any) -> None:
    _require_mapping(narratives, "workspace snapshot narratives")
    _require_keys(
        narratives,
        {
            "primary",
            "secondary",
            "mapping_coverage",
            "candidate_narratives",
            "excluded_mapping_candidates",
            "unmapped_holdings",
        },
        "workspace snapshot narratives",
    )
    _require_mapping(narratives["primary"], "workspace snapshot narratives.primary")
    _require_keys(
        narratives["primary"],
        {
            "narrative_id",
            "name",
            "normalized_exposure",
            "raw_exposure",
            "confidence",
            "state",
        },
        "workspace snapshot narratives.primary",
    )
    _require_mapping(
        narratives["primary"]["state"],
        "workspace snapshot narratives.primary.state",
    )
    _require_keys(
        narratives["primary"]["state"],
        {"stage", "sustainability_score", "confidence", "dimensions"},
        "workspace snapshot narratives.primary.state",
    )
    for field in {
        "secondary",
        "candidate_narratives",
        "excluded_mapping_candidates",
        "unmapped_holdings",
    }:
        if not isinstance(narratives[field], list):
            raise ProviderContractError(
                f"workspace snapshot narratives.{field} must be a list"
            )
    _require_mapping(
        narratives["mapping_coverage"],
        "workspace snapshot narratives.mapping_coverage",
    )
    _require_keys(
        narratives["mapping_coverage"],
        {
            "coverage_ratio",
            "covered_holding_count",
            "total_holding_count",
            "mapping_methods",
        },
        "workspace snapshot narratives.mapping_coverage",
    )


def _validate_workspace_snapshot_reports(reports: Any) -> None:
    _require_mapping(reports, "workspace snapshot reports")
    _require_keys(reports, {"markdown", "html"}, "workspace snapshot reports")
    for key in {"markdown", "html"}:
        _require_mapping(reports[key], f"workspace snapshot reports.{key}")
        _require_keys(
            reports[key],
            {"path", "format"},
            f"workspace snapshot reports.{key}",
        )
        if not isinstance(reports[key]["path"], str) or not reports[key]["path"]:
            raise ProviderContractError(
                f"workspace snapshot reports.{key}.path must be a non-empty string"
            )
        if Path(reports[key]["path"]).is_absolute() or ".." in Path(
            reports[key]["path"]
        ).parts:
            raise ProviderContractError(
                f"workspace snapshot reports.{key}.path must be relative"
            )
        if reports[key]["format"] != key:
            raise ProviderContractError(
                f"workspace snapshot reports.{key}.format mismatch"
            )


def _validate_workspace_snapshot_approval_workflow(approval_workflow: Any) -> None:
    _require_mapping(approval_workflow, "workspace snapshot approval_workflow")
    _require_keys(
        approval_workflow,
        {
            "status",
            "read_only",
            "requires_user_approval",
            "preview_command",
            "persist_command",
        },
        "workspace snapshot approval_workflow",
    )
    if approval_workflow["status"] != "ready_for_future_web":
        raise ProviderContractError(
            "workspace snapshot approval_workflow.status is unsupported"
        )
    for field in {"read_only", "requires_user_approval"}:
        if not isinstance(approval_workflow[field], bool):
            raise ProviderContractError(
                f"workspace snapshot approval_workflow.{field} must be boolean"
            )


def _require_mapping(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise ProviderContractError(f"{context} must be an object")


def _layers_by_name(layers: list[Any]) -> dict[str, Any]:
    result = {}
    for layer in layers:
        _require_mapping(layer, "source table layer")
        _require_keys(layer, SOURCE_TABLE_LAYER_REQUIRED_FIELDS, "source table layer")
        layer_name = layer.get("layer")
        if not isinstance(layer_name, str) or not layer_name:
            raise ProviderContractError("source table layer.layer must be a non-empty string")
        for field in {
            "display_name",
            "provider_name",
            "provider_version",
            "source_url",
        }:
            if not isinstance(layer[field], str) or not layer[field]:
                raise ProviderContractError(
                    f"source table layer.{field} must be a non-empty string"
                )
        if layer["data_quality"] not in SOURCE_TABLE_LAYER_DATA_QUALITIES:
            raise ProviderContractError(
                "source table layer.data_quality must be fresh, partial, mock, "
                "or unavailable"
            )
        if not isinstance(layer["is_mock"], bool):
            raise ProviderContractError("source table layer.is_mock must be boolean")
        review_metadata = layer.get("review_metadata")
        if review_metadata is not None:
            _require_mapping(review_metadata, "source table layer.review_metadata")
        if layer_name in result:
            raise ProviderContractError(
                f"source table layer.layer must be unique: {layer_name}"
            )
        result[layer_name] = layer
    return result


def _require_keys(value: dict[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ProviderContractError(f"{context} missing required fields: {missing}")


def _require_probability(value: Any, context: str) -> None:
    if not isinstance(value, int | float):
        raise ProviderContractError(f"{context} must be numeric")
    if value < 0 or value > 1:
        raise ProviderContractError(f"{context} must be within [0, 1]")


def _require_string_list(value: Any, context: str) -> None:
    if not isinstance(value, list):
        raise ProviderContractError(f"{context} must be a list")
    if not all(isinstance(item, str) for item in value):
        raise ProviderContractError(f"{context} must contain strings only")


def _validate_candidate_narrative(candidate: Any, context: str) -> str:
    _require_mapping(candidate, context)
    _require_keys(
        candidate,
        {
            "candidate_narrative_id",
            "name",
            "canonical_taxonomy",
            "status",
            "source",
            "triggering_stock_codes",
            "related_exclusion_ids",
            "aliases",
            "related_terms",
            "rationale",
            "human_review_status",
            "reviewed_by",
            "reviewed_at",
            "first_seen_at",
            "last_updated_at",
        },
        context,
    )
    candidate_id = candidate["candidate_narrative_id"]
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ProviderContractError(f"{context}.candidate_narrative_id must be a non-empty string")
    _require_string_list(
        candidate["triggering_stock_codes"],
        f"{context}.triggering_stock_codes",
    )
    _require_string_list(
        candidate["related_exclusion_ids"],
        f"{context}.related_exclusion_ids",
    )
    _require_string_list(candidate["aliases"], f"{context}.aliases")
    _require_string_list(candidate["related_terms"], f"{context}.related_terms")
    return candidate_id


def _validate_pipeline_manifest_artifacts(artifacts: Any) -> None:
    _require_mapping(artifacts, "pipeline artifact manifest artifacts")
    expected_formats = {
        "raw": "json",
        "scoring": "json",
        "review_queue": "json",
        "source_table": "json",
        "markdown": "markdown",
        "html": "html",
    }
    _require_keys(
        artifacts,
        set(expected_formats),
        "pipeline artifact manifest artifacts",
    )
    for key, expected_format in expected_formats.items():
        context = f"pipeline artifact manifest artifacts.{key}"
        artifact = artifacts[key]
        _require_mapping(artifact, context)
        _require_keys(artifact, {"path", "format"}, context)
        path = artifact["path"]
        if not isinstance(path, str) or not path:
            raise ProviderContractError(f"{context}.path must be a non-empty string")
        if path.startswith("/") or ".." in path.split("/"):
            raise ProviderContractError(f"{context}.path must be a relative file path")
        if artifact["format"] != expected_format:
            raise ProviderContractError(f"{context}.format must be {expected_format}")


def _validate_review_queue_exclusion(exclusion: Any, context: str) -> None:
    _require_mapping(exclusion, context)
    _require_keys(
        exclusion,
        {
            "exclusion_id",
            "stock_code",
            "stock_name",
            "narrative_id",
            "narrative_name",
            "method",
            "reason",
            "recommended_action",
        },
        context,
    )
    for field in {
        "exclusion_id",
        "stock_code",
        "stock_name",
        "narrative_id",
        "narrative_name",
        "method",
        "reason",
        "recommended_action",
    }:
        if not isinstance(exclusion[field], str) or not exclusion[field]:
            raise ProviderContractError(f"{context}.{field} must be a non-empty string")


def _validate_candidate_review_queue(queue: Any, candidate_ids: set[str]) -> None:
    _require_mapping(queue, "candidate_review_queue")
    _require_keys(queue, {"version", "summary", "items"}, "candidate_review_queue")
    if queue["version"] != "candidate-review-queue-v1":
        raise ProviderContractError("candidate_review_queue version is unsupported")
    items = queue["items"]
    if not isinstance(items, list):
        raise ProviderContractError("candidate_review_queue.items must be a list")
    item_candidate_ids = []
    for index, item in enumerate(items):
        item_candidate_ids.append(
            _validate_candidate_review_queue_item(
                item,
                candidate_ids,
                f"candidate_review_queue.items[{index}]",
            )
        )
    if len(set(item_candidate_ids)) != len(item_candidate_ids):
        raise ProviderContractError(
            "candidate_review_queue.items candidate_narrative_id values must be unique"
        )
    if set(item_candidate_ids) != candidate_ids:
        raise ProviderContractError(
            "candidate_review_queue.items must match candidate_narratives"
        )
    _validate_candidate_review_queue_summary(queue["summary"], items)


def _validate_candidate_review_queue_summary(
    summary: Any,
    items: list[Any],
) -> None:
    _require_mapping(summary, "candidate_review_queue.summary")
    _require_keys(
        summary,
        {"total_count", "pending_count", "action_required"},
        "candidate_review_queue.summary",
    )
    pending_count = sum(
        1
        for item in items
        if isinstance(item, dict) and item.get("human_review_status") == "candidate"
    )
    if summary["total_count"] != len(items):
        raise ProviderContractError(
            "candidate_review_queue.summary.total_count must match item count"
        )
    if summary["pending_count"] != pending_count:
        raise ProviderContractError(
            "candidate_review_queue.summary.pending_count must match pending items"
        )
    if summary["action_required"] != (pending_count > 0):
        raise ProviderContractError(
            "candidate_review_queue.summary.action_required must match pending_count"
        )


def _validate_candidate_review_queue_item(
    item: Any,
    candidate_ids: set[str],
    context: str,
) -> str:
    _require_mapping(item, context)
    _require_keys(
        item,
        {
            "review_item_id",
            "item_type",
            "candidate_narrative_id",
            "name",
            "canonical_taxonomy",
            "status",
            "human_review_status",
            "source",
            "rationale",
            "triggering_stock_codes",
            "related_exclusion_ids",
            "related_exclusions",
            "available_actions",
            "default_action",
            "requires_promotion_metadata",
            "promotion_action_template",
        },
        context,
    )
    candidate_id = item["candidate_narrative_id"]
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ProviderContractError(f"{context}.candidate_narrative_id must be a non-empty string")
    if candidate_id not in candidate_ids:
        raise ProviderContractError(
            f"{context}.candidate_narrative_id must exist in candidate_narratives"
        )
    if item["review_item_id"] != f"RQ_{candidate_id}":
        raise ProviderContractError(f"{context}.review_item_id must match candidate")
    if item["item_type"] != "candidate_narrative":
        raise ProviderContractError(f"{context}.item_type is unsupported")
    _require_string_list(item["triggering_stock_codes"], f"{context}.triggering_stock_codes")
    _require_string_list(item["related_exclusion_ids"], f"{context}.related_exclusion_ids")
    related_exclusions = item["related_exclusions"]
    if not isinstance(related_exclusions, list):
        raise ProviderContractError(f"{context}.related_exclusions must be a list")
    for index, exclusion in enumerate(related_exclusions):
        _validate_review_queue_exclusion(
            exclusion,
            f"{context}.related_exclusions[{index}]",
        )
    if item["available_actions"] != ["approve", "reject", "defer"]:
        raise ProviderContractError(f"{context}.available_actions is unsupported")
    if item["default_action"] not in item["available_actions"]:
        raise ProviderContractError(f"{context}.default_action must be available")
    if not isinstance(item["requires_promotion_metadata"], bool):
        raise ProviderContractError(f"{context}.requires_promotion_metadata must be boolean")
    _validate_review_queue_promotion_template(
        item["promotion_action_template"],
        candidate_id,
        f"{context}.promotion_action_template",
    )
    return candidate_id


def _validate_review_queue_promotion_template(
    template: Any,
    candidate_id: str,
    context: str,
) -> None:
    _require_mapping(template, context)
    _require_keys(
        template,
        {
            "action_id",
            "candidate_narrative_id",
            "action",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "promotion",
        },
        context,
    )
    if template["candidate_narrative_id"] != candidate_id:
        raise ProviderContractError(f"{context}.candidate_narrative_id must match item")
    if template["action"] != "approve":
        raise ProviderContractError(f"{context}.action must be approve")
    promotion = template["promotion"]
    _require_mapping(promotion, f"{context}.promotion")
    _require_keys(
        promotion,
        {"narrative_id", "parent_id", "level", "aliases", "related_terms"},
        f"{context}.promotion",
    )
    if not isinstance(promotion["level"], int) or promotion["level"] <= 0:
        raise ProviderContractError(f"{context}.promotion.level must be positive integer")
    _require_string_list(promotion["aliases"], f"{context}.promotion.aliases")
    _require_string_list(promotion["related_terms"], f"{context}.promotion.related_terms")


def _validate_review_action_preview_summary(summary: Any) -> None:
    _require_mapping(summary, "review action preview summary")
    _require_keys(
        summary,
        {
            "action",
            "candidate_narrative_id",
            "candidate_status_after",
            "human_review_status_after",
            "active_narrative_count_before",
            "active_narrative_count_after",
            "promotion_target_id",
            "source_registry_written",
            "requires_explicit_persistence_step",
        },
        "review action preview summary",
    )
    if summary["action"] not in {"approve", "reject", "defer"}:
        raise ProviderContractError("review action preview summary action is invalid")
    for field in {
        "candidate_narrative_id",
        "candidate_status_after",
        "human_review_status_after",
    }:
        if not isinstance(summary[field], str) or not summary[field]:
            raise ProviderContractError(
                f"review action preview summary {field} must be a non-empty string"
            )
    for field in {"active_narrative_count_before", "active_narrative_count_after"}:
        if not isinstance(summary[field], int) or summary[field] < 0:
            raise ProviderContractError(
                f"review action preview summary {field} must be a non-negative integer"
            )
    if summary["promotion_target_id"] is not None and not isinstance(
        summary["promotion_target_id"], str
    ):
        raise ProviderContractError(
            "review action preview summary promotion_target_id must be null or string"
        )
    for field in {"source_registry_written", "requires_explicit_persistence_step"}:
        if not isinstance(summary[field], bool):
            raise ProviderContractError(
                f"review action preview summary {field} must be boolean"
            )


def _validate_review_action_registry_delta(delta: Any) -> None:
    _require_mapping(delta, "review action preview registry_delta")
    _require_keys(
        delta,
        {
            "active_narrative_ids_added",
            "active_narrative_count_change",
            "candidate_changes",
        },
        "review action preview registry_delta",
    )
    _require_string_list(
        delta["active_narrative_ids_added"],
        "review action preview registry_delta.active_narrative_ids_added",
    )
    if not isinstance(delta["active_narrative_count_change"], int):
        raise ProviderContractError(
            "review action preview registry_delta.active_narrative_count_change must be integer"
        )
    _validate_review_action_candidate_changes(delta["candidate_changes"])


def _validate_review_action_persistence_overwrite_policy(policy: Any) -> None:
    _require_mapping(policy, "review action persistence result overwrite_policy")
    _require_keys(
        policy,
        {
            "allow_registry_overwrite",
            "allow_output_overwrite",
            "allow_result_overwrite",
        },
        "review action persistence result overwrite_policy",
    )
    for field in {
        "allow_registry_overwrite",
        "allow_output_overwrite",
        "allow_result_overwrite",
    }:
        if not isinstance(policy[field], bool):
            raise ProviderContractError(f"overwrite_policy.{field} must be boolean")


def _validate_review_action_candidate_changes(candidate_changes: Any) -> None:
    _require_mapping(candidate_changes, "review action preview candidate_changes")
    _require_keys(
        candidate_changes,
        {"candidate_narrative_id", "before", "after"},
        "review action preview candidate_changes",
    )
    if not isinstance(candidate_changes["candidate_narrative_id"], str) or not (
        candidate_changes["candidate_narrative_id"]
    ):
        raise ProviderContractError(
            "review action preview candidate_changes.candidate_narrative_id must be a non-empty string"
        )
    _validate_candidate_review_projection(
        candidate_changes["before"],
        "review action preview candidate_changes.before",
    )
    _validate_candidate_review_projection(
        candidate_changes["after"],
        "review action preview candidate_changes.after",
    )


def _validate_candidate_review_projection(projection: Any, context: str) -> None:
    _require_mapping(projection, context)
    _require_keys(
        projection,
        {
            "status",
            "human_review_status",
            "reviewed_by",
            "reviewed_at",
            "promotion_target_id",
        },
        context,
    )
