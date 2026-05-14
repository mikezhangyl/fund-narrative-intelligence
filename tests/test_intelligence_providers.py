from src.providers.intelligence import (
    MockAnnouncementProvider,
    MockIntelligenceProviderSet,
    MockMarketDataProvider,
    MockNewsEvidenceProvider,
    MockValuationProvider,
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
