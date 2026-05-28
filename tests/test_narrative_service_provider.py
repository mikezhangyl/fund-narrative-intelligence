import yaml
from scripts.run_fund_holding_exposure_report import load_intelligence_context
from src.config import (
    DEFAULT_CANDIDATE_NARRATIVE_EVENTS_PATH,
    DEFAULT_MAPPING_EVIDENCE_PACKS_PATH,
    DEFAULT_REVIEWED_REGISTRY_PATH,
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    PROJECT_ROOT,
)
from src.providers.narrative_service import (
    FallbackNarrativeDataProvider,
    LocalNarrativePrototypeProvider,
    NarrativeServiceProvider,
    build_narrative_data_provider,
)


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


def test_fund_holding_exposure_loader_uses_local_prototype_for_reviewed_inputs(
    monkeypatch,
):
    monkeypatch.delenv("NARRATIVE_SERVICE_URL", raising=False)

    registry, mappings, source = load_intelligence_context(
        registry_mode="reviewed",
        stock_mapping_mode="reviewed",
    )

    assert registry["trust_metadata"]["trust_status"] == "untrusted_experimental"
    assert mappings
    assert {mapping["source_trust_status"] for mapping in mappings} == {
        "untrusted_experimental"
    }
    assert source["source"] == "local_prototype"


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
        "GET /api/v1/narratives/review-actions",
        "POST /api/v1/narratives/review-actions",
    }
    assert payload["trust_policy"]["automatic_ingestion_may_create"] == [
        "candidate_narratives",
        "candidate_stock_mappings",
        "candidate_evidence_packs",
        "review_queue_items",
        "review_action_records",
    ]
    assert "trusted_stock_mappings" in payload["trust_policy"]["automatic_ingestion_must_not_create"]


def test_narrative_service_provider_fetches_report_inputs(monkeypatch):
    requested: list[tuple[str, str]] = []

    def fake_request_json(*, method, url, payload, timeout_seconds):
        del payload
        del timeout_seconds
        requested.append((method, url))
        if url.endswith("/registry"):
            data = {
                "version": "registry-v1",
                "narratives": [{"narrative_id": "N_AI", "name": "AI"}],
                "candidate_narratives": [],
                "trust_metadata": {"trust_status": "trusted_validated"},
            }
        elif url.endswith("/mappings"):
            data = {
                "mappings": [
                    {
                        "stock_code": "000001",
                        "narrative_id": "N_AI",
                        "confidence": 0.8,
                    }
                ]
            }
        else:
            data = {}
        return {
            "status": "available",
            "source": "narrative_service",
            "provider": "fake-service",
            "provider_version": "fake-v1",
            "data": data,
            "warnings": [],
            "trust_metadata": {"trust_status": "trusted_validated"},
        }

    monkeypatch.setattr(
        "src.providers.narrative_service._request_json",
        fake_request_json,
    )

    provider = NarrativeServiceProvider(base_url="http://127.0.0.1:9999")
    registry, mappings = provider.get_report_inputs()

    assert registry["version"] == "registry-v1"
    assert mappings == [
        {"stock_code": "000001", "narrative_id": "N_AI", "confidence": 0.8}
    ]
    assert ("GET", "http://127.0.0.1:9999/api/v1/narratives/registry") in requested
    assert ("GET", "http://127.0.0.1:9999/api/v1/narratives/mappings") in requested


def test_build_narrative_data_provider_uses_service_first_when_configured(monkeypatch):
    monkeypatch.setenv("NARRATIVE_SERVICE_URL", "http://127.0.0.1:9999")

    provider = build_narrative_data_provider()

    assert isinstance(provider, FallbackNarrativeDataProvider)
    assert isinstance(provider.primary, NarrativeServiceProvider)
    assert provider.primary.base_url == "http://127.0.0.1:9999"


def test_fallback_narrative_provider_discloses_service_failure(monkeypatch):
    monkeypatch.delenv("NARRATIVE_SERVICE_URL", raising=False)

    class BrokenProvider:
        def get_snapshot(self):
            raise RuntimeError("service unavailable")

        def get_report_inputs(self):
            raise RuntimeError("service unavailable")

    provider = FallbackNarrativeDataProvider(
        primary=BrokenProvider(),
        fallback=LocalNarrativePrototypeProvider(),
    )

    snapshot = provider.get_snapshot()

    assert snapshot["source"] == "local_prototype"
    assert snapshot["diagnostics"]["service_ready"] is False
    assert snapshot["warnings"][0]["code"] == "NARRATIVE_SERVICE_FALLBACK"
    assert "service unavailable" in snapshot["warnings"][0]["message"]
