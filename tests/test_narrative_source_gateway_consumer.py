from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest
from scripts import run_narrative_source_gateway_probe as probe
from src.market_data.gateway_contract import load_gateway_contract
from src.market_data.providers.narrative_source_gateway import (
    GatewaySourceUnavailableError,
    NarrativeSourceGatewayClient,
    normalize_gateway_source_event,
)


def _gateway_row(**overrides):
    row = {
        "source_event_id": "sevt-sec-aapl-20260531",
        "source_type": "filing",
        "source_provider": "sec_edgar",
        "source_url": "https://www.sec.gov/Archives/edgar/data/320193/sample.htm",
        "title": "Apple 8-K filing",
        "event_time": "2026-05-31T10:00:00Z",
        "fetched_at": "2026-05-31T10:01:00Z",
        "trust_tier": "official_primary",
        "source_quality": "trusted_fact_candidate",
        "license_scope": "metadata_and_public_filing_reference",
        "retention_policy": "metadata_and_permitted_excerpt",
        "metadata_only": False,
        "degradation_events": [],
        "summary": "Official filing sample",
        "stock_codes": ["AAPL"],
        "narrative_hints": ["AI devices"],
    }
    return {**row, **overrides}


def test_gateway_contract_declares_narrative_source_event_endpoints():
    contract = load_gateway_contract()

    unified = contract.endpoint("gateway_narrative_source_events")
    filing = contract.endpoint("gateway_narrative_official_filings")
    disclosure = contract.endpoint("gateway_narrative_official_disclosures")
    news = contract.endpoint("gateway_narrative_news_context")
    heat = contract.endpoint("gateway_narrative_social_heat")

    assert unified.provider == "gateway"
    assert unified.method == "GET"
    assert unified.path == "/api/v1/market-data/narrative/source-events"
    assert unified.dataset_id == "narrative_source_events"
    assert unified.required_request_fields == ("source_kind", "limit")
    assert unified.sample_request["query"]["source_kind"] == "official_filings,official_disclosures"
    assert unified.sample_request["query"]["keyword"] == "AI infrastructure"
    assert filing.provider == "gateway"
    assert filing.path == "/api/v1/market-data/narrative/source-events/official-filings"
    assert disclosure.dataset_id == "narrative_official_disclosures"
    assert news.dataset_id == "narrative_news_context"
    assert heat.dataset_id == "narrative_social_heat"
    for endpoint in (unified, filing, disclosure, news, heat):
        assert endpoint.rows_path == "data.rows"
        assert "trust_tier" in endpoint.required_response_fields
        assert "source_quality" in endpoint.required_response_fields
        assert "license_scope" in endpoint.required_response_fields
        assert "retention_policy" in endpoint.required_response_fields
        assert "metadata_only" in endpoint.required_response_fields
        assert "degradation_events" in endpoint.required_response_fields


def test_narrative_source_gateway_client_normalizes_mock_gateway_rows():
    calls = []

    def fetcher(method, url, body, timeout_seconds):
        calls.append((method, url, body, timeout_seconds))
        return 200, {
            "data": {"rows": [_gateway_row()]},
            "meta": {
                "provider": "gateway",
                "endpoint": "narrative_source_events",
                "generated_at": "2026-05-31T10:02:00Z",
                "cache": {"hit": True, "mode": "cache"},
            },
        }

    client = NarrativeSourceGatewayClient(
        base_url="http://localhost:8700",
        timeout_seconds=3.0,
        fetcher=fetcher,
    )

    result = client.fetch_source_events(
        source_kind="official_filings",
        symbols=["AAPL"],
        query="Apple",
        limit=5,
    )

    assert result["status"] == "completed"
    assert result["row_count"] == 1
    assert result["rows"][0]["event_id"] == "sevt-sec-aapl-20260531"
    assert result["rows"][0]["provider"] == "gateway_sec_edgar"
    assert result["rows"][0]["trust_tier"] == "official_primary"
    assert result["rows"][0]["source_quality"] == "trusted_fact_candidate"
    assert result["rows"][0]["metadata_only"] is False
    assert calls[0][0] == "GET"
    assert calls[0][2] is None
    assert calls[0][3] == 3.0
    parsed = urlparse(calls[0][1])
    assert parsed.path == "/api/v1/market-data/narrative/source-events"
    assert parse_qs(parsed.query) == {
        "source_kind": ["official_filings"],
        "symbol": ["AAPL"],
        "keyword": ["Apple"],
        "limit": ["5"],
    }


def test_narrative_source_gateway_client_preserves_gateway_degraded_status():
    def fetcher(method, url, body, timeout_seconds):
        del method, url, body, timeout_seconds
        return 200, {
            "data": {"rows": []},
            "meta": {
                "status": "degraded",
                "degradation_events": [
                    {
                        "code": "SOCIAL_SOURCE_DISABLED",
                        "message": "Social source disabled by policy.",
                    }
                ],
                "pagination": {"next_cursor": None},
            },
        }

    client = NarrativeSourceGatewayClient(
        base_url="http://localhost:8700",
        fetcher=fetcher,
    )

    result = client.fetch_source_events(source_kind="social_heat", symbols=["AAPL"])

    assert result["status"] == "degraded"
    assert result["row_count"] == 0
    assert result["degradation_events"][0]["code"] == "SOCIAL_SOURCE_DISABLED"


def test_narrative_source_gateway_client_fails_clearly_when_route_unavailable():
    def fetcher(method, url, body, timeout_seconds):
        del method, url, body, timeout_seconds
        return 404, {"error": {"code": "ROUTE_NOT_FOUND", "message": "not mounted"}}

    client = NarrativeSourceGatewayClient(
        base_url="http://localhost:8700",
        fetcher=fetcher,
    )

    with pytest.raises(GatewaySourceUnavailableError) as exc:
        client.fetch_source_events(source_kind="news_context", query="半导体", limit=5)

    assert "gateway narrative source route unavailable" in str(exc.value)
    assert "ROUTE_NOT_FOUND" in str(exc.value)


def test_normalize_gateway_source_event_rejects_missing_quality_labels():
    with pytest.raises(ValueError, match="trust_tier"):
        normalize_gateway_source_event(_gateway_row(trust_tier=""))


def test_probe_report_renders_chinese_html_and_json_quality_labels(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "official_filings": {
                    "data": {"rows": [_gateway_row()]},
                    "meta": {"provider": "gateway"},
                },
                "social_heat": {
                    "data": {
                        "rows": [
                            _gateway_row(
                                source_event_id="sevt-heat-aapl",
                                source_type="social",
                                source_provider="stocktwits",
                                trust_tier="heat_signal_only",
                                source_quality="context_only",
                                license_scope="metadata_and_permitted_excerpt",
                                retention_policy="metadata_only",
                                metadata_only=True,
                                degradation_events=[
                                    {
                                        "code": "heat_only",
                                        "message": "Social heat cannot satisfy trusted evidence.",
                                    }
                                ],
                            )
                        ]
                    },
                    "meta": {"provider": "gateway"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = probe.main(
        [
            "--base-url",
            "http://localhost:8700",
            "--source-kind",
            "official_filings",
            "--source-kind",
            "social_heat",
            "--fixture-json",
            str(fixture_path),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 0
    payload = json.loads((tmp_path / "out" / "narrative_source_gateway_probe.json").read_text())
    html = (tmp_path / "out" / "narrative_source_gateway_probe.html").read_text()

    assert payload["summary"]["completed_source_kinds"] == 2
    assert payload["source_results"][0]["rows"][0]["trust_tier"] == "official_primary"
    assert "叙事来源 Gateway 消费探针" in html
    assert "official_primary" in html
    assert "heat_signal_only" in html
    assert "metadata_only" in html
    assert "不能把未支持的候选信号表述为确定事实" in html


def test_probe_default_source_kinds_cover_gateway_m20_sources():
    assert probe.DEFAULT_SOURCE_KINDS == (
        "official_filings",
        "official_disclosures",
        "official_sources",
        "news_context",
        "open_news_index",
        "industry_media",
        "social_heat",
    )
