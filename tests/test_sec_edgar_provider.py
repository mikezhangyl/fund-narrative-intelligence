from __future__ import annotations

import json

from scripts import run_sec_edgar_source_smoke
from src.providers.sec_edgar import (
    SEC_EDGAR_PROVIDER_NAME,
    SecEdgarSubmissionsProvider,
    render_sec_edgar_smoke_html,
)


def test_sec_edgar_provider_normalizes_fixture_source_events():
    provider = SecEdgarSubmissionsProvider(fetcher=lambda _url, _headers: _sec_fixture())

    payload = provider.get_submissions(
        cik="320193",
        ticker="AAPL",
        company_name="Apple Inc.",
        limit=5,
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    assert payload["version"] == "sec-edgar-submissions-v1"
    assert payload["provider_name"] == SEC_EDGAR_PROVIDER_NAME
    assert payload["data_quality"] == "fresh"
    assert payload["summary"] == {
        "requested_cik": "0000320193",
        "event_count": 5,
        "skipped_filing_count": 0,
        "degradation_count": 0,
    }
    assert [event["source_metadata"]["event_class"] for event in payload["events"]] == [
        "current_report",
        "annual_report",
        "quarterly_report",
        "foreign_report",
        "insider_ownership",
    ]
    first = payload["events"][0]
    assert first["source_type"] == "filing"
    assert first["source_trust_tier"] == "trusted_fact"
    assert first["trust_status"] == "candidate_untrusted"
    assert first["source_metadata"]["provider"] == SEC_EDGAR_PROVIDER_NAME
    assert first["source_metadata"]["cik"] == "0000320193"
    assert first["source_metadata"]["ticker"] == "AAPL"
    assert first["source_metadata"]["company_name"] == "Apple Inc."
    assert first["source_metadata"]["form_type"] == "8-K"
    assert first["source_metadata"]["accession_number"] == "0000320193-26-000001"
    assert first["source_metadata"]["source_trust_tier"] == "trusted_fact"
    assert first["source_metadata"]["evidence_granularity"] == "metadata_only"
    assert len(first["source_metadata"]["raw_hash"]) == 64
    assert first["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019326000001/0000320193-26-000001-index.html"
    )


def test_sec_edgar_provider_returns_structured_degradation_on_failure():
    def failing_fetcher(_url: str, _headers: dict[str, str]) -> dict[str, object]:
        raise TimeoutError("network timeout")

    payload = SecEdgarSubmissionsProvider(fetcher=failing_fetcher).get_submissions(
        cik="0000320193",
        ticker="AAPL",
        company_name="Apple Inc.",
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    assert payload["data_quality"] == "unavailable"
    assert payload["events"] == []
    assert payload["summary"]["degradation_count"] == 1
    assert payload["degradation_events"] == [
        {
            "type": "provider_unavailable",
            "provider_name": SEC_EDGAR_PROVIDER_NAME,
            "reason": "SEC EDGAR submissions fetch failed for 0000320193: network timeout",
        }
    ]


def test_sec_edgar_html_summary_is_chinese_and_discloses_trust_tier():
    payload = SecEdgarSubmissionsProvider(fetcher=lambda _url, _headers: _sec_fixture()).get_submissions(
        cik="320193",
        ticker="AAPL",
        company_name="Apple Inc.",
        limit=1,
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    html = render_sec_edgar_smoke_html(payload)

    assert "<h1>SEC EDGAR 官方披露事件</h1>" in html
    assert "trusted_fact" in html
    assert "metadata_only" in html
    assert "不解析全文或 XBRL" in html
    assert "0000320193-26-000001" in html


def test_sec_edgar_smoke_cli_writes_json_and_chinese_html(tmp_path):
    fixture_path = tmp_path / "sec_fixture.json"
    fixture_path.write_text(json.dumps(_sec_fixture()), encoding="utf-8")
    output_dir = tmp_path / "outputs"

    exit_code = run_sec_edgar_source_smoke.main(
        [
            "--cik",
            "320193",
            "--ticker",
            "AAPL",
            "--company-name",
            "Apple Inc.",
            "--limit",
            "2",
            "--input-json",
            str(fixture_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    output = json.loads((output_dir / "sec_edgar_source_smoke.json").read_text())
    html = (output_dir / "sec_edgar_source_smoke.html").read_text()

    assert output["summary"]["event_count"] == 2
    assert output["events"][0]["source_trust_tier"] == "trusted_fact"
    assert "<h1>SEC EDGAR 官方披露事件</h1>" in html


def _sec_fixture() -> dict[str, object]:
    return {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "tickers": ["AAPL"],
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0000320193-26-000001",
                    "0000320193-26-000002",
                    "0000320193-26-000003",
                    "0000320193-26-000004",
                    "0000320193-26-000005",
                ],
                "filingDate": [
                    "2026-05-29",
                    "2026-05-01",
                    "2026-04-20",
                    "2026-04-15",
                    "2026-04-10",
                ],
                "reportDate": [
                    "2026-05-29",
                    "2026-03-31",
                    "2026-03-31",
                    "2026-04-15",
                    "2026-04-10",
                ],
                "form": ["8-K", "10-K", "10-Q", "6-K", "4"],
                "primaryDocument": [
                    "aapl-20260529.htm",
                    "aapl-20260331.htm",
                    "aapl-20260331x10q.htm",
                    "aapl-6k.htm",
                    "xslF345X05/wk-form4_1.xml",
                ],
                "primaryDocDescription": [
                    "Current report",
                    "Annual report",
                    "Quarterly report",
                    "Foreign issuer report",
                    "Statement of changes in beneficial ownership",
                ],
            }
        },
    }
