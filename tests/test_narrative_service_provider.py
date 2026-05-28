import yaml
from scripts.run_fund_holding_exposure_report import load_intelligence_context
from src.config import (
    DEFAULT_CANDIDATE_NARRATIVE_EVENTS_PATH,
    DEFAULT_MAPPING_EVIDENCE_PACKS_PATH,
    DEFAULT_REVIEWED_REGISTRY_PATH,
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    PROJECT_ROOT,
)
from src.providers.narrative_service import LocalNarrativePrototypeProvider


def test_local_narrative_prototype_provider_returns_contract_snapshot():
    provider = LocalNarrativePrototypeProvider()

    snapshot = provider.get_snapshot()

    assert snapshot["status"] == "available"
    assert snapshot["source"] == "local_prototype"
    assert snapshot["narrative_registry"]["trust_metadata"]["trust_status"] == (
        "untrusted_experimental"
    )
    assert snapshot["stock_narrative_mappings"]
    assert {mapping["source_trust_status"] for mapping in snapshot["stock_narrative_mappings"]} == {
        "untrusted_experimental"
    }
    assert snapshot["mapping_evidence_packs"]["trust_status"] == "candidate_untrusted"
    assert snapshot["candidate_intake_events"]["version"] == "candidate-narrative-events-v1"
    assert snapshot["provider_layers"]["narrative_registry"]["source_url"].startswith(
        "reviewed-registry://"
    )
    assert snapshot["provider_layers"]["mapping_evidence_packs"]["source_url"].startswith(
        "local-prototype://"
    )
    assert snapshot["diagnostics"]["local_fallback"] is True
    assert snapshot["diagnostics"]["service_ready"] is False


def test_local_narrative_prototype_provider_returns_deep_copies():
    provider = LocalNarrativePrototypeProvider()

    snapshot = provider.get_snapshot()
    snapshot["narrative_registry"]["narratives"][0]["name"] = "mutated"
    snapshot["stock_narrative_mappings"][0]["confidence"] = 0.0
    snapshot["mapping_evidence_packs"]["packs"][0]["stock_code"] = "mutated"
    snapshot["candidate_intake_events"]["events"][0]["event_id"] = "mutated"

    fresh = provider.get_snapshot()

    assert fresh["narrative_registry"]["narratives"][0]["name"] != "mutated"
    assert fresh["stock_narrative_mappings"][0]["confidence"] != 0.0
    assert fresh["mapping_evidence_packs"]["packs"][0]["stock_code"] != "mutated"
    assert fresh["candidate_intake_events"]["events"][0]["event_id"] != "mutated"


def test_local_narrative_prototype_provider_can_expose_legacy_report_inputs():
    provider = LocalNarrativePrototypeProvider()

    registry, mappings = provider.get_report_inputs()

    assert registry["version"] == "registry-v1"
    assert mappings
    assert all(mapping["stock_code"] for mapping in mappings)


def test_fund_holding_exposure_loader_uses_local_prototype_for_reviewed_inputs():
    registry, mappings = load_intelligence_context(
        registry_mode="reviewed",
        stock_mapping_mode="reviewed",
    )

    assert registry["trust_metadata"]["trust_status"] == "untrusted_experimental"
    assert mappings
    assert {mapping["source_trust_status"] for mapping in mappings} == {
        "untrusted_experimental"
    }


def test_narrative_service_contract_declares_required_surfaces():
    contract_path = PROJECT_ROOT / "config" / "narrative_service_contract.yaml"

    payload = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert payload["version"] == "narrative-service-contract-v1"
    assert payload["ownership"]["service_owner"] == "narrative-service"
    assert payload["fallback"]["local_prototype"]["registry_path"] == str(
        DEFAULT_REVIEWED_REGISTRY_PATH.relative_to(PROJECT_ROOT)
    )
    assert payload["fallback"]["local_prototype"]["mappings_path"] == str(
        DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH.relative_to(PROJECT_ROOT)
    )
    assert payload["fallback"]["local_prototype"]["evidence_packs_path"] == str(
        DEFAULT_MAPPING_EVIDENCE_PACKS_PATH.relative_to(PROJECT_ROOT)
    )
    assert payload["fallback"]["local_prototype"]["candidate_events_path"] == str(
        DEFAULT_CANDIDATE_NARRATIVE_EVENTS_PATH.relative_to(PROJECT_ROOT)
    )
    assert {
        route["method"] + " " + route["path"] for route in payload["endpoints"]
    } >= {
        "GET /api/v1/narratives/registry",
        "GET /api/v1/narratives/mappings",
        "POST /api/v1/narratives/intake/events",
        "GET /api/v1/narratives/evidence-packs",
        "GET /api/v1/narratives/trust-audits/latest",
        "GET /api/v1/narratives/review-queue",
    }
    assert payload["trust_policy"]["automatic_ingestion_may_create"] == [
        "candidate_narratives",
        "candidate_stock_mappings",
        "candidate_evidence_packs",
        "review_queue_items",
    ]
    assert "trusted_stock_mappings" in payload["trust_policy"]["automatic_ingestion_must_not_create"]
