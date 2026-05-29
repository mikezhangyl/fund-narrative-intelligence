from __future__ import annotations

import json
from pathlib import Path

from scripts import run_announcement_mapping_intake
from src.scanners.announcement_mapping_intake import (
    announcement_events_to_evidence_packs,
    build_announcement_mapping_intake_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_announcement_events_convert_to_candidate_mapping_evidence():
    packs = announcement_events_to_evidence_packs(
        event_payload=_event_payload(),
        registry_payload=_registry_payload(),
    )

    assert [pack["stock_code"] for pack in packs] == ["300308", "600519"]
    optical_mapping = packs[0]["proposed_mappings"][0]
    assert optical_mapping["narrative_id"] == "N_OPTICAL_MODULE_CHAIN"
    assert optical_mapping["target_is_existing_narrative"] is True
    assert optical_mapping["trust_status"] == "candidate_untrusted"
    assert optical_mapping["evidence_items"][0]["source_type"] == "announcement"
    assert optical_mapping["evidence_items"][0]["supported_claim_types"] == [
        "business_relevance",
        "specificity",
    ]
    assert optical_mapping["evidence_items"][0]["quality_gaps"] == []

    baijiu_mapping = packs[1]["proposed_mappings"][0]
    assert baijiu_mapping["evidence_items"][0]["quality_gaps"] == [
        "missing_source_url",
        "missing_event_time",
    ]


def test_announcement_mapping_intake_report_stays_reviewable_and_untrusted():
    report = build_announcement_mapping_intake_report(
        event_payload=_event_payload(),
        registry_payload=_registry_payload(),
    )

    assert report["version"] == "announcement-mapping-intake-v1"
    assert report["status"] == "candidate_untrusted"
    assert report["summary"]["announcement_event_count"] == 2
    assert report["summary"]["candidate_mapping_count"] == 2
    assert report["summary"]["quality_gap_count"] == 2
    assert report["promotion_decision"] == {
        "can_write_to_reviewed_mapping_store": False,
        "required_next_step": "human_review",
    }
    assert report["evidence_detail_view"][0]["supported_claim_types"] == [
        "business_relevance",
        "specificity",
    ]
    assert "trusted_validated" not in json.dumps(report, ensure_ascii=False)


def test_run_announcement_mapping_intake_writes_json_and_html(tmp_path):
    events_path = tmp_path / "events.json"
    registry_path = tmp_path / "registry.json"
    events_path.write_text(json.dumps(_event_payload(), ensure_ascii=False), encoding="utf-8")
    registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_announcement_mapping_intake.main(
        [
            "--events-path",
            str(events_path),
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "announcement_mapping_intake_report.json").read_text())
    html = (tmp_path / "announcement_mapping_intake_report.html").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["summary"]["candidate_mapping_count"] == 2
    assert "公告证据详情" in html
    assert "missing_source_url" in html
    assert "candidate_untrusted" in html


def _event_payload() -> dict:
    return json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "announcement_events_for_mapping_intake.v1.json")
        .read_text(encoding="utf-8")
    )


def _registry_payload() -> dict:
    return {
        "version": "registry-v1",
        "narratives": [
            {
                "narrative_id": "N_OPTICAL_MODULE_CHAIN",
                "display_name": "光模块",
                "name": "光模块产业链",
                "aliases": ["光模块产业链"],
                "related_terms": ["光模块", "光通信"],
            },
            {
                "narrative_id": "N_BAIJIU_CONSUMPTION",
                "display_name": "高端白酒消费",
                "name": "高端白酒消费",
                "aliases": ["白酒消费"],
                "related_terms": ["白酒", "消费"],
            },
        ],
    }
