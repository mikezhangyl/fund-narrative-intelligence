from __future__ import annotations

import json

import pytest
from scripts import run_source_schema_v2_report as report_script
from src.scanners.source_schema_v2 import (
    load_source_schema_v2,
    source_event_v2_to_v1,
    validate_source_event_v2,
)


def _source_event(**overrides):
    event = {
        "source_id": "sec_edgar_filings",
        "source_event_id": "sevt-v2-sec-aapl",
        "source_class": "official_disclosure",
        "provider": "sec_edgar",
        "source_url": "https://www.sec.gov/Archives/edgar/data/320193/sample.htm",
        "fetched_at": "2026-06-01T01:00:00Z",
        "published_at": "2026-06-01T00:00:00Z",
        "license_scope": "metadata_and_public_document_reference",
        "retention_policy": "metadata_and_permitted_excerpt",
        "raw_hash": "sha256:" + "a" * 64,
        "title": "Apple 8-K filing",
        "text_excerpt": "Apple filed an 8-K.",
        "entities": [{"entity_type": "ticker", "value": "AAPL"}],
        "topics": ["AI infrastructure"],
        "event_type": "filing",
        "extraction_method": "gateway_normalized",
        "confidence": 0.91,
        "source_trust_tier": "official_primary",
        "freshness_bucket": "fresh",
        "evidence_ids": ["evd-aapl-8k"],
        "contradiction_flags": [],
        "dispute_flags": [],
        "metadata_only": False,
    }
    return {**event, **overrides}


def test_source_schema_v2_declares_required_entities_and_source_classes():
    schema = load_source_schema_v2()

    assert schema["version"] == "narrative-source-schema-v2"
    assert set(schema["entities"]) >= {
        "SourceEvent",
        "NarrativeFact",
        "CandidateNarrative",
        "EvidencePack",
        "SourceQuality",
    }
    assert set(schema["supported_source_classes"]) >= {
        "official_disclosure",
        "licensed_news",
        "public_web",
        "social_community",
    }
    assert "raw_content_policy" in schema["entities"]["SourceEvent"]["required_fields"]
    assert "text_excerpt" in schema["entities"]["SourceEvent"]["required_fields"]


def test_valid_source_event_v2_passes_with_retention_and_excerpt_policy():
    normalized = validate_source_event_v2(
        _source_event(
            raw_content_policy={
                "raw_retention_allowed": False,
                "excerpt_retention_allowed": True,
                "max_excerpt_chars": 500,
            }
        )
    )

    assert normalized["schema_version"] == "narrative-source-schema-v2"
    assert normalized["source_class"] == "official_disclosure"
    assert normalized["source_quality"]["source_trust_tier"] == "official_primary"
    assert normalized["raw_content_policy"]["excerpt_retention_allowed"] is True


def test_source_event_v2_requires_raw_hash_and_extraction_fields():
    with pytest.raises(ValueError, match="raw_hash"):
        validate_source_event_v2(
            _source_event(
                raw_hash="",
                raw_content_policy={"raw_retention_allowed": False},
            )
        )


def test_source_event_v2_supports_social_heat_without_trusted_promotion():
    normalized = validate_source_event_v2(
        _source_event(
            source_class="social_community",
            provider="stocktwits",
            source_trust_tier="heat_signal_only",
            event_type="social_heat",
            metadata_only=True,
            raw_content_policy={
                "raw_retention_allowed": False,
                "excerpt_retention_allowed": True,
                "max_excerpt_chars": 280,
            },
        )
    )

    assert normalized["source_quality"]["source_trust_tier"] == "heat_signal_only"
    assert normalized["promotion_effect"] == "none"
    assert normalized["trust_status"] == "candidate_untrusted"


def test_source_event_v2_can_feed_existing_v1_fixture_workflow():
    v1_event = source_event_v2_to_v1(
        _source_event(
            raw_content_policy={
                "raw_retention_allowed": False,
                "excerpt_retention_allowed": True,
            }
        )
    )

    assert v1_event["schema_version"] == "source-event-schema-v1"
    assert v1_event["event_id"] == "sevt-v2-sec-aapl"
    assert v1_event["source_type"] == "filing"
    assert v1_event["provider"] == "sec_edgar"
    assert v1_event["trust_status"] == "candidate_untrusted"
    assert v1_event["direct_crawling_allowed"] is False


def test_source_schema_v2_report_outputs_json_and_chinese_html(tmp_path):
    exit_code = report_script.main(["--output-dir", str(tmp_path / "out")])

    assert exit_code == 0
    payload = json.loads((tmp_path / "out" / "source_schema_v2_report.json").read_text())
    html = (tmp_path / "out" / "source_schema_v2_report.html").read_text()

    assert payload["schema_version"] == "narrative-source-schema-v2"
    assert payload["summary"]["entity_count"] >= 5
    assert "SourceEvent" in payload["entities"]
    assert "叙事来源 Schema v2 报告" in html
    assert "raw_content_policy" in html
    assert "EvidencePack" in html
