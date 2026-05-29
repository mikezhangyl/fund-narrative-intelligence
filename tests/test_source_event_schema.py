from __future__ import annotations

import json
from pathlib import Path

from src.scanners.candidate_narrative_intake import (
    build_candidate_narrative_intake_report,
)
from src.scanners.source_event_schema import (
    normalize_source_event,
    source_event_dedupe_key,
    validate_source_event,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_news_and_announcement_fixtures_validate_against_one_schema():
    payload = json.loads(
        (
            PROJECT_ROOT / "data" / "fixtures" / "source_events.news_announcement.v1.json"
        ).read_text(encoding="utf-8")
    )

    normalized = [validate_source_event(event) for event in payload["events"]]

    assert {event["source_type"] for event in normalized} == {"news", "announcement"}
    for event in normalized:
        assert event["schema_version"] == "source-event-schema-v1"
        assert event["dedupe_key"] == source_event_dedupe_key(event)
        assert event["trust_status"] == "candidate_untrusted"
        assert event["promotion_effect"] == "none"
        assert event["source_metadata"]["source_mode"] in {
            "normalized_gateway",
            "local_fixture",
        }


def test_source_event_validation_records_quality_gaps_without_crawling_policy():
    event = normalize_source_event(
        {
            "source_type": "news",
            "provider": "gateway_news_briefs",
            "title": "Missing metadata sample",
            "summary": "No URL, event_time, or stock code should be a quality gap.",
            "narrative_hints": ["机器人"],
            "evidence_claims": ["source mentions robotics demand"],
        }
    )

    assert event["quality_gaps"] == [
        "missing_source_url",
        "missing_event_time",
        "missing_stock_codes",
    ]
    assert event["external_access_policy"] == "gateway_change_request_first"
    assert event["direct_crawling_allowed"] is False


def test_candidate_intake_report_references_source_event_schema_and_stays_untrusted():
    event_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "fixtures" / "source_events.news_announcement.v1.json"
        ).read_text(encoding="utf-8")
    )
    registry_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "registry" / "narrative_registry.reviewed.json"
        ).read_text(encoding="utf-8")
    )

    report = build_candidate_narrative_intake_report(
        event_payload=event_payload,
        registry_payload=registry_payload,
    )

    assert report["source_event_schema"]["version"] == "source-event-schema-v1"
    assert report["status"] == "candidate_untrusted"
    assert {event["source_type"] for event in report["events"]} == {
        "news",
        "announcement",
    }
    assert all(event["dedupe_key"] for event in report["events"])
    assert "trusted_validated" not in json.dumps(report, ensure_ascii=False)


def test_gateway_change_request_protocol_is_documented_and_reflected_in_inventory():
    document = (
        PROJECT_ROOT
        / "docs"
        / "product"
        / "gateway-narrative-source-change-request-protocol-2026-05-29.md"
    ).read_text(encoding="utf-8")
    inventory = (PROJECT_ROOT / "config" / "data_capabilities.yaml").read_text(
        encoding="utf-8"
    )

    for term in [
        "dataset",
        "provider preference",
        "endpoint semantics",
        "fallback behavior",
        "validation matrix",
        "sample consumer request",
        "gateway_change_request_first",
        "stock-data-gateway",
    ]:
        assert term in document

    assert "narrative_source_events" in inventory
    assert "gateway_change_request_first" in inventory
