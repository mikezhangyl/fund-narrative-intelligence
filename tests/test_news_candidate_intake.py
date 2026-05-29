from __future__ import annotations

import json
from pathlib import Path

from scripts import run_news_candidate_intake
from src.scanners.news_candidate_intake import (
    build_news_candidate_intake_report,
    news_briefs_to_source_events,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_news_briefs_convert_to_source_events_without_direct_crawling():
    payload = _news_payload()

    events = news_briefs_to_source_events(
        news_payload=payload,
        provider="gateway_news_briefs",
        source_provider="tushare",
        src="sina",
    )

    assert [event["source_type"] for event in events] == ["news", "news"]
    assert {event["provider"] for event in events} == {"gateway_news_briefs"}
    assert all(event["source_metadata"]["source_mode"] == "normalized_gateway" for event in events)
    assert all(event["trust_status"] == "candidate_untrusted" for event in events)
    assert all(event["promotion_effect"] == "none" for event in events)
    assert all(event["direct_crawling_allowed"] is False for event in events)
    assert events[0]["candidate_narratives"][0]["name"] == "机器人执行器"
    assert events[1]["candidate_narratives"][0]["narrative_id"] == "N_BAIJIU_CONSUMPTION"
    assert events[1]["source_metadata"]["raw_provider"] == "tushare"
    assert events[1]["source_metadata"]["raw_src"] == "sina"


def test_news_candidate_intake_report_marks_new_and_reinforced_candidates_untrusted():
    report = build_news_candidate_intake_report(
        news_payload=_news_payload(),
        registry_payload=_registry_payload(),
        provider="gateway_news_briefs",
        source_provider="tushare",
        src="sina",
    )

    assert report["version"] == "news-candidate-intake-v1"
    assert report["status"] == "candidate_untrusted"
    assert report["news_source_contract"] == {
        "input": "gateway_or_tushare_news_briefs",
        "provider": "gateway_news_briefs",
        "source_provider": "tushare",
        "src": "sina",
        "direct_crawling_allowed": False,
    }
    assert report["summary"]["event_count"] == 2
    assert report["summary"]["new_candidate_narrative_count"] == 1
    assert report["summary"]["existing_narrative_evidence_count"] == 1
    assert report["new_candidate_narratives"][0]["name"] == "机器人执行器"
    assert report["existing_narrative_evidence"][0]["narrative_id"] == "N_BAIJIU_CONSUMPTION"
    assert "trusted_validated" not in json.dumps(report, ensure_ascii=False)


def test_run_news_candidate_intake_writes_json_and_html(tmp_path):
    news_path = tmp_path / "news.json"
    registry_path = tmp_path / "registry.json"
    news_path.write_text(json.dumps(_news_payload(), ensure_ascii=False), encoding="utf-8")
    registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_news_candidate_intake.main(
        [
            "--news-briefs-path",
            str(news_path),
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "news_candidate_intake_report.json").read_text())
    html = (tmp_path / "news_candidate_intake_report.html").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["status"] == "candidate_untrusted"
    assert payload["summary"]["event_count"] == 2
    assert "机器人执行器" in html
    assert "已有叙事证据补强" in html


def _news_payload() -> dict:
    return json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "news_briefs_for_candidate_intake.v1.json")
        .read_text(encoding="utf-8")
    )


def _registry_payload() -> dict:
    return {
        "version": "registry-v1",
        "narratives": [
            {
                "narrative_id": "N_BAIJIU_CONSUMPTION",
                "display_name": "高端白酒消费",
                "name": "高端白酒消费",
                "aliases": ["白酒消费"],
                "related_terms": ["白酒", "消费"],
            }
        ],
    }
