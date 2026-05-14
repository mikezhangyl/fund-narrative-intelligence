import json

from src.config import FIXTURE_DIR
from src.errors import FixtureNotFoundError
from src.providers.intelligence import (
    MockAnnouncementProvider,
    MockIntelligenceProviderSet,
    MockMarketDataProvider,
    MockNewsEvidenceProvider,
    MockValuationProvider,
    ReviewedNarrativeRegistryProvider,
    ReviewedStockNarrativeMappingProvider,
)
from src.providers.mock import MockDataProvider


def test_mock_intelligence_provider_set_loads_validated_fixture_layers():
    providers = MockIntelligenceProviderSet()

    registry = providers.get_narrative_registry()
    mappings = providers.get_stock_narrative_mappings()
    exclusions = providers.get_mapping_exclusions()
    evidence = providers.get_evidence()
    signals = providers.get_signal_events()

    assert registry["version"] == "registry-v1"
    assert {
        item["candidate_narrative_id"]
        for item in registry["candidate_narratives"]
    } >= {
        "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
        "C_COMMUNICATION_POWER_INFRASTRUCTURE",
    }
    assert all(
        item["human_review_status"] == "candidate"
        for item in registry["candidate_narratives"]
    )
    assert mappings
    assert exclusions["version"] == "mapping-exclusions-v1"
    assert {
        (item["stock_code"], item["narrative_id"]) for item in exclusions["exclusions"]
    } >= {
        ("688036", "N_SEMI_CAPEX"),
        ("688692", "N_SEMI_CAPEX"),
        ("600522", "N_SEMI_CAPEX"),
    }
    assert evidence[0]["source"].startswith("mock_")
    assert signals[0]["signal_id"]


def test_mock_intelligence_provider_set_returns_deep_copies():
    providers = MockIntelligenceProviderSet()

    evidence = providers.get_evidence()
    original_title = evidence[0]["title"]
    evidence[0]["title"] = "mutated"

    assert providers.get_evidence()[0]["title"] == original_title


def test_mock_intelligence_provider_set_exposes_layer_provenance():
    providers = MockIntelligenceProviderSet()

    layers = providers.get_provider_layers()

    assert set(layers) == {
        "narrative_registry",
        "stock_mappings",
        "evidence",
        "signals",
    }
    assert all(layer["is_mock"] is True for layer in layers.values())
    assert layers["evidence"]["provider_name"] == "mock-fixture-provider"
    assert "evidence.json" in layers["evidence"]["note"]


def test_reviewed_narrative_registry_provider_loads_validated_store(tmp_path):
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text(
        _reviewed_registry_text(),
        encoding="utf-8",
    )
    provider = ReviewedNarrativeRegistryProvider(registry_path=registry_path)

    registry = provider.get_narrative_registry()
    registry["narratives"][0]["name"] = "mutated"
    fresh_registry = provider.get_narrative_registry()
    layer = provider.get_provider_layer()

    assert fresh_registry["version"] == "registry-v1"
    assert fresh_registry["narratives"][0]["name"] != "mutated"
    assert layer["layer"] == "narrative_registry"
    assert layer["provider_name"] == "reviewed-registry-store"
    assert layer["provider_version"] == "reviewed-registry-v1"
    assert layer["data_quality"] == "fresh"
    assert layer["source_url"].startswith("reviewed-registry://external/")
    assert "/narrative_registry.reviewed.json#sha256=" in layer["source_url"]
    assert layer["is_mock"] is False
    assert layer["review_metadata"]["reviewed_by"] == "seed-curation"
    assert layer["review_metadata"]["review_schema_version"] == "review-metadata-v1"


def test_reviewed_narrative_registry_provider_rejects_missing_audit_metadata(
    tmp_path,
):
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    provider = ReviewedNarrativeRegistryProvider(registry_path=registry_path)

    try:
        provider.get_narrative_registry()
    except ValueError as exc:
        assert "review_metadata" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing registry audit metadata")


def test_reviewed_narrative_registry_provider_rejects_unreviewed_approved_entry(
    tmp_path,
):
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    payload = json.loads(_reviewed_registry_text())
    payload["narratives"][0]["reviewed_by"] = None
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    provider = ReviewedNarrativeRegistryProvider(registry_path=registry_path)

    try:
        provider.get_narrative_registry()
    except ValueError as exc:
        assert "narratives[0].reviewed_by" in str(exc)
    else:
        raise AssertionError("expected ValueError for unreviewed approved narrative")


def test_reviewed_narrative_registry_provider_rejects_non_object_store(tmp_path):
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text(json.dumps([]), encoding="utf-8")
    provider = ReviewedNarrativeRegistryProvider(registry_path=registry_path)

    try:
        provider.get_narrative_registry()
    except ValueError as exc:
        assert "must contain a JSON object" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-object reviewed registry")


def test_reviewed_narrative_registry_provider_rejects_missing_store(tmp_path):
    provider = ReviewedNarrativeRegistryProvider(
        registry_path=tmp_path / "missing.reviewed.json"
    )

    try:
        provider.get_narrative_registry()
    except FixtureNotFoundError as exc:
        assert "Missing reviewed registry" in str(exc)
    else:
        raise AssertionError("expected FixtureNotFoundError for missing store")


def test_reviewed_stock_mapping_provider_loads_validated_store(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    mappings_path.write_text(_reviewed_mapping_text(), encoding="utf-8")
    provider = ReviewedStockNarrativeMappingProvider(mappings_path=mappings_path)

    mappings = provider.get_stock_narrative_mappings()
    mappings[0]["confidence"] = 0.0
    fresh_mappings = provider.get_stock_narrative_mappings()
    layer = provider.get_provider_layer()

    assert fresh_mappings[0]["confidence"] != 0.0
    assert {mapping["method"] for mapping in fresh_mappings} == {"reviewed_mapping"}
    assert layer["layer"] == "stock_mappings"
    assert layer["provider_name"] == "reviewed-mapping-store"
    assert layer["provider_version"] == "reviewed-mapping-v1"
    assert layer["data_quality"] == "partial"
    assert layer["source_url"].startswith("reviewed-mapping://external/")
    assert "/stock_narrative_mappings.reviewed.json#sha256=" in layer["source_url"]
    assert layer["is_mock"] is False
    assert layer["review_metadata"]["reviewed_by"] == "seed-curation"
    assert layer["review_metadata"]["review_schema_version"] == "review-metadata-v1"


def test_reviewed_stock_mapping_provider_rejects_missing_audit_metadata(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    mappings_path.write_text(
        (FIXTURE_DIR / "stock_narrative_mappings.json")
        .read_text(encoding="utf-8")
        .replace('"method": "fixture_rule"', '"method": "reviewed_mapping"'),
        encoding="utf-8",
    )
    provider = ReviewedStockNarrativeMappingProvider(mappings_path=mappings_path)

    try:
        provider.get_stock_narrative_mappings()
    except ValueError as exc:
        assert "review_metadata" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing mapping audit metadata")


def test_reviewed_stock_mapping_provider_rejects_unapproved_mapping_review(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    payload = json.loads(_reviewed_mapping_text())
    payload["mappings"][0]["review"]["status"] = "pending"
    mappings_path.write_text(json.dumps(payload), encoding="utf-8")
    provider = ReviewedStockNarrativeMappingProvider(mappings_path=mappings_path)

    try:
        provider.get_stock_narrative_mappings()
    except ValueError as exc:
        assert "review.status must be approved" in str(exc)
    else:
        raise AssertionError("expected ValueError for unapproved mapping review")


def test_reviewed_stock_mapping_provider_rejects_non_reviewed_methods(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    payload = json.loads(_reviewed_mapping_text())
    payload["mappings"][0]["method"] = "fixture_rule"
    mappings_path.write_text(json.dumps(payload), encoding="utf-8")
    provider = ReviewedStockNarrativeMappingProvider(mappings_path=mappings_path)

    try:
        provider.get_stock_narrative_mappings()
    except ValueError as exc:
        assert "method reviewed_mapping" in str(exc)
        assert "fixture_rule" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-reviewed mapping method")


def test_mock_data_provider_uses_intelligence_layer_provenance():
    provider = MockDataProvider()
    fund_payload = provider.get_fund_holdings("000001")

    foundation = provider.get_provider_foundation(
        fund_provider_metadata=fund_payload["fund"]["provider_metadata"],
        degradation_events=[],
    )

    assert foundation["effective_data_quality"] == "mock"
    assert foundation["layers"]["evidence"]["note"].endswith("evidence.json.")
    assert foundation["layers"]["signals"]["note"].endswith("signal_events.json.")


def test_reserved_mock_source_providers_return_stable_empty_payloads():
    market_data = MockMarketDataProvider().get_stock_quotes(["NVDA", "MSFT"])
    valuation = MockValuationProvider().get_valuation_snapshots(["NVDA"])
    announcements = MockAnnouncementProvider().get_announcements(
        stock_codes=["NVDA"],
        as_of_date="2026-05-13",
    )
    news = MockNewsEvidenceProvider().get_news_evidence(
        narrative_ids=["N_AI_INFRA"],
        as_of_date="2026-05-13",
    )

    assert market_data == {
        "version": "market-data-mock-v1",
        "data_quality": "mock",
        "quotes": [],
        "missing_stock_codes": ["MSFT", "NVDA"],
    }
    assert valuation == {
        "version": "valuation-mock-v1",
        "data_quality": "mock",
        "valuations": [],
        "missing_stock_codes": ["NVDA"],
    }
    assert announcements == {
        "version": "announcement-mock-v1",
        "data_quality": "mock",
        "announcements": [],
        "missing_stock_codes": ["NVDA"],
    }
    assert news == {
        "version": "news-evidence-mock-v1",
        "data_quality": "mock",
        "evidence": [],
        "missing_narrative_ids": ["N_AI_INFRA"],
    }


def _reviewed_registry_text() -> str:
    payload = json.loads((FIXTURE_DIR / "narrative_registry.json").read_text())
    payload["review_metadata"] = {
        "review_schema_version": "review-metadata-v1",
        "reviewed_by": "seed-curation",
        "reviewed_at": "2026-05-15",
        "review_note": "Seeded reviewed registry for V1 provider validation.",
    }
    for narrative in payload["narratives"]:
        narrative["reviewed_by"] = "seed-curation"
        narrative["reviewed_at"] = "2026-05-15"
    return json.dumps(payload, ensure_ascii=False)


def _reviewed_mapping_text() -> str:
    payload = json.loads((FIXTURE_DIR / "stock_narrative_mappings.json").read_text())
    payload["review_metadata"] = {
        "review_schema_version": "review-metadata-v1",
        "reviewed_by": "seed-curation",
        "reviewed_at": "2026-05-15",
        "review_note": "Seeded reviewed mappings for V1 provider validation.",
    }
    for mapping in payload["mappings"]:
        mapping["method"] = "reviewed_mapping"
        mapping["review"] = {
            "status": "approved",
            "reviewed_by": "seed-curation",
            "reviewed_at": "2026-05-15",
            "review_note": "Seeded from accepted V1 mapping fixture.",
        }
    return json.dumps(payload, ensure_ascii=False)
