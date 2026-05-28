import json

from scripts import validate_narrative_intelligence_service
from src.orchestrator import run_pipeline
from src.providers import eastmoney as eastmoney_module


class FakeAnnouncementProvider:
    provider_name = "fake-announcements"
    provider_version = "fake-announcements-v1"

    def get_announcements(
        self,
        stock_codes: list[str],
        as_of_date: str,
        start_date: str | None = None,
    ) -> dict:
        del as_of_date, start_date
        assert stock_codes == ["777777"]
        return {
            "version": "announcement-v1",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": "fresh",
            "announcements": [
                {
                    "stock_code": "777777",
                    "stock_name": "PhotonLink",
                    "title": "PhotonLink wins optical interconnect order for AI clusters",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source": "exchange",
                    "source_url": "https://example.com/ai-cluster-order",
                },
                {
                    "stock_code": "777777",
                    "stock_name": "PhotonLink",
                    "title": "PhotonLink expands optical interconnect switching platform",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source": "exchange",
                    "source_url": "https://example.com/interconnect-platform",
                },
            ],
            "missing_stock_codes": [],
        }


def test_narrative_intelligence_acceptance_passes_for_generated_candidates(
    tmp_path, monkeypatch
):
    def fake_fetcher(_url: str) -> dict:
        return {
            "Success": True,
            "Expansion": "2026-03-31",
            "Datas": {
                "fundStocks": [
                    {
                        "GPDM": "777777",
                        "GPJC": "PhotonLink",
                        "JZBL": "8.88",
                        "PCTNVCHG": "0",
                        "INDEXNAME": "Communications Infrastructure",
                    }
                ]
            },
        }

    monkeypatch.setattr(eastmoney_module, "_fetch_json", fake_fetcher)
    run_pipeline(
        fund_code="161725",
        provider_mode="eastmoney",
        output_dir=tmp_path,
        include_announcement_evidence=True,
        announcement_provider=FakeAnnouncementProvider(),
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    validate_narrative_intelligence_service.validate_acceptance_outputs(
        output_dir=tmp_path,
        fund_code="161725",
        require_generated_candidates=True,
    )


def test_narrative_intelligence_acceptance_rejects_missing_generated_candidates(
    tmp_path,
):
    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
    )
    raw = json.loads(artifacts["raw"].read_text())
    raw["generated_candidate_narratives"] = []
    artifacts["raw"].write_text(json.dumps(raw), encoding="utf-8")

    try:
        validate_narrative_intelligence_service.validate_acceptance_outputs(
            output_dir=tmp_path,
            fund_code="000001",
            require_generated_candidates=True,
        )
    except validate_narrative_intelligence_service.AcceptanceError as exc:
        assert "generated candidate narratives are required" in str(exc)
    else:
        raise AssertionError("expected generated candidate validation failure")
