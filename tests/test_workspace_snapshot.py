import json

import pytest
from src.errors import ProviderContractError
from src.modules.workspace_snapshot.builder import build_workspace_snapshot
from src.orchestrator import run_pipeline
from src.validation import validate_workspace_snapshot_payload


def test_build_workspace_snapshot_from_output_directory(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)

    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())

    validate_workspace_snapshot_payload(snapshot)
    assert snapshot_path.name == "fund_000001_workspace_snapshot.json"
    assert snapshot["version"] == "workspace-snapshot-v1"
    assert snapshot["fund_code"] == "000001"
    assert snapshot["artifact_manifest"]["artifacts"]["source_table"]["path"] == (
        "fund_000001_source_table.json"
    )
    assert snapshot["artifact_manifest"]["artifacts"]["signal_trace"]["path"] == (
        "fund_000001_signal_trace.json"
    )
    assert snapshot["signal_trace"]["version"] == "signal-trace-v1"
    assert snapshot["signal_trace"]["fund_code"] == "000001"
    assert snapshot["signal_trace"]["provider_foundation"] == snapshot[
        "provider_foundation"
    ]
    assert snapshot["data_layers"]["version"] == "workspace-data-layers-v1"
    assert snapshot["data_layers"]["fund_code"] == "000001"
    layers_by_name = {
        layer["layer"]: layer for layer in snapshot["data_layers"]["layers"]
    }
    assert layers_by_name["holdings"] == {
        "layer": "holdings",
        "provider_name": "mock-fixture-provider",
        "data_quality": "mock",
        "is_mock": True,
        "source_url": "mock://fixtures/fund_000001.json",
        "artifact": "raw",
        "item_count": 10,
        "available": True,
    }
    assert layers_by_name["signal_events"]["source_url"] == (
        "mock://fixtures/signal_events.json"
    )
    assert layers_by_name["signal_events"]["item_count"] > 0
    assert snapshot["source_table"]["layers"][0]["source_url"].startswith(
        "mock://fixtures/"
    )
    assert snapshot["data_source_notice"] == {
        "display_required": True,
        "severity": "mock",
        "effective_data_quality": "mock",
        "message": snapshot["provider_foundation"]["disclosure_message"],
        "mock_layer_count": 5,
        "unavailable_layer_count": 0,
        "degradation_event_count": 0,
        "layers_requiring_disclosure": [
            {
                "layer": layer["layer"],
                "display_name": layer["display_name"],
                "provider_name": layer["provider_name"],
                "data_quality": layer["data_quality"],
                "source_url": layer["source_url"],
                "is_mock": layer["is_mock"],
            }
            for layer in snapshot["provider_foundation"]["layers"].values()
        ],
    }
    assert snapshot["review_queue"]["candidate_review_queue"]["version"] == (
        "candidate-review-queue-v1"
    )
    assert snapshot["approval_workflow"]["status"] == "ready_for_future_web"
    assert snapshot["approval_workflow"]["read_only"] is True
    assert snapshot["approval_workflow"]["review_queue_summary"] == {
        "total_count": 0,
        "pending_count": 0,
        "action_required": False,
    }
    assert snapshot["approval_workflow"]["available_actions"] == []
    assert snapshot["approval_workflow"]["review_item_count"] == 0
    assert snapshot["approval_workflow"]["pending_review_item_count"] == 0
    assert snapshot["narratives"]["primary"]["narrative_id"]


def test_workspace_snapshot_preserves_valuation_layer_for_future_web(tmp_path):
    class FakeMarketDataProvider:
        provider_name = "eastmoney-market-quote"
        provider_version = "eastmoney-market-quote-v1"
        source_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        degradation_events: list[dict[str, str]] = []

        def get_stock_quotes(self, stock_codes: list[str]) -> dict:
            assert "NVDA" in stock_codes
            return {
                "version": self.provider_version,
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "quotes": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "source_provider": "eastmoney",
                        "source_url": self.source_url,
                        "latest_price": 106.0,
                        "change_percent": 6.0,
                        "change_amount": 6.0,
                        "volume": 100,
                        "amount": 10600.0,
                        "high": 107.0,
                        "low": 99.0,
                        "open": 100.0,
                        "previous_close": 100.0,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                    }
                ],
                "missing_stock_codes": [],
            }

    run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_market_quotes=True,
        include_valuation_snapshots=True,
        market_data_provider=FakeMarketDataProvider(),
    )

    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())

    validate_workspace_snapshot_payload(snapshot)
    valuation_layer = snapshot["provider_foundation"]["layers"]["valuation"]
    assert valuation_layer["provider_name"] == "quote-derived-valuation"
    assert "not a full fundamental valuation feed" in valuation_layer["note"]
    assert {layer["layer"] for layer in snapshot["source_table"]["layers"]} >= {
        "valuation"
    }


def test_workspace_snapshot_preserves_news_layer_for_future_web(tmp_path):
    class FakeNewsEvidenceProvider:
        provider_name = "google-news-rss"
        provider_version = "google-news-rss-v1"
        source_url = "https://news.google.com/rss/search"

        def get_news_evidence(self, narratives: list[dict], as_of_date: str) -> dict:
            del as_of_date
            return {
                "version": "news-evidence-v1",
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "query_scope": {
                    "requested_narrative_ids": [],
                    "queried_narrative_ids": [
                        narrative["narrative_id"] for narrative in narratives
                    ],
                    "omitted_narrative_ids": [],
                    "query_limit": 4,
                },
                "evidence": [
                    {
                        "evidence_id": "EV_NEWS_N_AI_INFRA_TEST",
                        "narrative_id": narratives[0]["narrative_id"],
                        "type": "news",
                        "source": "google_news_rss",
                        "source_url": "https://example.com/news/ai",
                        "title": "AI infrastructure growth accelerates",
                        "summary": (
                            "Example News headline/snippet matched the narrative "
                            "query. V1 classified only RSS title/snippet text; "
                            "article body content was not parsed."
                        ),
                        "sentiment": "positive",
                        "confidence": 0.52,
                        "event_date": "2026-05-14",
                        "source_provider": self.provider_name,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                        "provider_data_quality": "fresh",
                        "classification_reason": "keyword heuristic over RSS title/snippet",
                    }
                ],
                "missing_narrative_ids": [],
                "skipped_item_count": 0,
                "degradation_events": [],
            }

    run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_news_evidence=True,
        news_evidence_provider=FakeNewsEvidenceProvider(),
    )

    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())

    validate_workspace_snapshot_payload(snapshot)
    news_layer = snapshot["provider_foundation"]["layers"]["news_evidence"]
    assert news_layer["provider_name"] == "google-news-rss"
    assert "titles/snippets only" in news_layer["note"]
    assert {layer["layer"] for layer in snapshot["source_table"]["layers"]} >= {
        "news_evidence"
    }
    data_layers = {layer["layer"]: layer for layer in snapshot["data_layers"]["layers"]}
    assert data_layers["news_evidence"]["item_count"] == 1
    assert data_layers["news_evidence"]["provider_name"] == "google-news-rss"
    assert data_layers["news_evidence"]["is_mock"] is False


def test_workspace_snapshot_preserves_financial_metrics_layer_for_future_web(tmp_path):
    class FakeFinancialMetricsProvider:
        provider_name = "eastmoney-financial-metrics"
        provider_version = "eastmoney-financial-metrics-v1"
        source_url = "https://datacenter.eastmoney.com/securities/api/data/get"
        degradation_events: list[dict[str, str]] = []

        def get_financial_metrics(self, stock_codes: list[str]) -> dict:
            assert "NVDA" in stock_codes
            return {
                "version": "financial-metrics-v1",
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-15T00:00:00+00:00",
                "metrics": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "report_date": "2026-03-31",
                        "report_type": "一季报",
                        "notice_date": "2026-04-25",
                        "currency": "USD",
                        "revenue_yoy": 18.0,
                        "parent_net_profit_yoy": 22.0,
                        "source": "provider_financial_metrics",
                        "source_provider": self.provider_name,
                        "source_url": self.source_url,
                        "retrieved_at": "2026-05-15T00:00:00+00:00",
                    }
                ],
                "missing_stock_codes": [],
            }

    run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_financial_metrics=True,
        financial_metrics_provider=FakeFinancialMetricsProvider(),
    )

    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())

    validate_workspace_snapshot_payload(snapshot)
    data_layers = {layer["layer"]: layer for layer in snapshot["data_layers"]["layers"]}
    assert data_layers["financial_metrics"] == {
        "layer": "financial_metrics",
        "provider_name": "eastmoney-financial-metrics",
        "data_quality": "fresh",
        "is_mock": False,
        "source_url": "https://datacenter.eastmoney.com/securities/api/data/get",
        "artifact": "raw",
        "item_count": 1,
        "available": True,
    }


def test_build_workspace_snapshot_rejects_announcement_payload_drift(tmp_path):
    _run_pipeline_with_announcement_payload(tmp_path)
    scoring_path = tmp_path / "fund_000001_scoring.json"
    scoring = json.loads(scoring_path.read_text())
    scoring["announcements"]["announcements"][0]["title"] = "mutated announcement title"
    scoring_path.write_text(json.dumps(scoring), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path)

    assert "workspace snapshot announcements mismatch" in str(exc.value)


def test_build_workspace_snapshot_rejects_announcement_evidence_payload_drift(tmp_path):
    _run_pipeline_with_announcement_payload(tmp_path)
    scoring_path = tmp_path / "fund_000001_scoring.json"
    scoring = json.loads(scoring_path.read_text())
    scoring["announcement_evidence"]["evidence"][0]["summary"] = "mutated summary"
    scoring_path.write_text(json.dumps(scoring), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path)

    assert "workspace snapshot announcement_evidence mismatch" in str(exc.value)


def test_workspace_snapshot_counts_announcement_evidence_for_future_web(tmp_path):
    _run_pipeline_with_announcement_payload(tmp_path)

    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())

    data_layers = {layer["layer"]: layer for layer in snapshot["data_layers"]["layers"]}
    assert data_layers["announcements"]["item_count"] == 1
    assert data_layers["announcement_evidence"]["item_count"] == 2


def test_build_workspace_snapshot_rejects_invalid_news_payload(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    raw_path = tmp_path / "fund_000001_raw.json"
    scoring_path = tmp_path / "fund_000001_scoring.json"
    raw = json.loads(raw_path.read_text())
    scoring = json.loads(scoring_path.read_text())
    raw["news_evidence"] = {"version": "news-evidence-v1"}
    scoring["news_evidence"] = raw["news_evidence"]
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    scoring_path.write_text(json.dumps(scoring), encoding="utf-8")

    with pytest.raises(ProviderContractError) as exc:
        build_workspace_snapshot(tmp_path)

    assert "news evidence missing required fields" in str(exc.value)


def test_workspace_snapshot_validation_rejects_identity_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["source_table"]["fund_code"] = "999999"

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "source table fund_code mismatch" in str(exc.value)


def test_workspace_snapshot_validation_rejects_signal_trace_identity_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["signal_trace"]["fund_code"] = "999999"

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "signal trace fund_code mismatch" in str(exc.value)


def test_workspace_snapshot_validation_rejects_source_notice_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["data_source_notice"]["display_required"] = False

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "data_source_notice display_required mismatch" in str(exc.value)


def test_workspace_snapshot_validation_rejects_data_layers_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["data_layers"]["fund_code"] = "999999"

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "workspace snapshot data_layers fund_code mismatch" in str(exc.value)


def test_workspace_snapshot_validation_rejects_approval_summary_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["approval_workflow"]["review_item_count"] = 99

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "approval_workflow review_item_count mismatch" in str(exc.value)


def test_build_workspace_snapshot_rejects_missing_report_file(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    (tmp_path / "fund_000001_report.md").unlink()

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path)

    assert "manifest artifact markdown does not exist" in str(exc.value)


def test_build_workspace_snapshot_rejects_external_output_path(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path, output_path=tmp_path.parent / "snapshot.json")

    assert "workspace snapshot output must stay in artifact directory" in str(exc.value)


def test_workspace_snapshot_validation_rejects_review_queue_identity_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["review_queue"]["metadata"]["fund_code"] = "999999"

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "review queue fund_code mismatch" in str(exc.value)


def test_workspace_snapshot_validation_rejects_incomplete_narrative_payload(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["narratives"]["primary"] = {}

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "narratives.primary missing required fields" in str(exc.value)


def _run_pipeline_with_announcement_payload(tmp_path):
    class FakeAnnouncementProvider:
        provider_name = "cninfo-announcement"
        provider_version = "cninfo-announcement-v1"
        source_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        degradation_events: list[dict[str, str]] = []

        def get_announcements(
            self,
            stock_codes: list[str],
            as_of_date: str,
            start_date: str | None = None,
        ) -> dict:
            assert "NVDA" in stock_codes
            assert as_of_date == "2026-05-13"
            assert start_date == "2026-05-01"
            return {
                "version": self.provider_version,
                "data_quality": "fresh",
                "announcements": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "title": "2026年度业绩预增公告",
                        "category": "业绩预告",
                        "announcement_date": "2026-05-12",
                        "source": "cninfo",
                        "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
                    }
                ],
                "missing_stock_codes": [],
            }

    run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_announcement_evidence=True,
        announcement_start_date="2026-05-01",
        announcement_provider=FakeAnnouncementProvider(),
    )
