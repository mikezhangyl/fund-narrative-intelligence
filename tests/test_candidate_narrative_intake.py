from __future__ import annotations

import json

from scripts import run_candidate_narrative_intake
from src.scanners.candidate_narrative_intake import (
    build_candidate_narrative_intake_report,
    render_html_report,
)


def test_candidate_narrative_intake_separates_new_existing_and_mapping_candidates():
    report = build_candidate_narrative_intake_report(
        event_payload=_event_payload(),
        registry_payload=_registry_payload(),
    )

    assert report["status"] == "candidate_untrusted"
    assert report["summary"] == {
        "event_count": 3,
        "source_type_count": 3,
        "new_candidate_narrative_count": 1,
        "existing_narrative_evidence_count": 1,
        "candidate_mapping_count": 4,
        "review_queue_item_count": 5,
    }
    assert report["source_type_counts"] == {
        "manual": 1,
        "news": 1,
        "social": 1,
    }
    assert report["new_candidate_narratives"][0]["name"] == "机器人执行器"
    assert report["new_candidate_narratives"][0]["trust_status"] == "candidate_untrusted"
    assert report["existing_narrative_evidence"][0]["narrative_id"] == "N_BAIJIU_CONSUMPTION"
    assert report["candidate_stock_mappings"][0]["stock_code"] == "300024"
    assert report["candidate_stock_mappings"][0]["trust_status"] == "candidate_untrusted"
    assert report["intake_review_queue"]["summary"] == {
        "total_count": 5,
        "candidate_narrative_count": 1,
        "candidate_mapping_count": 4,
        "action_required": True,
    }


def test_candidate_narrative_intake_html_contains_review_sections():
    report = build_candidate_narrative_intake_report(
        event_payload=_event_payload(),
        registry_payload=_registry_payload(),
    )

    html = render_html_report(report)

    assert "<h1>候选叙事接入口报告</h1>" in html
    assert "机器人执行器" in html
    assert "已有叙事证据补强" in html
    assert "候选股票映射" in html
    assert "candidate_untrusted" in html


def test_run_candidate_narrative_intake_writes_json_and_html(tmp_path):
    events_path = tmp_path / "events.json"
    registry_path = tmp_path / "registry.json"
    events_path.write_text(json.dumps(_event_payload()), encoding="utf-8")
    registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")

    exit_code = run_candidate_narrative_intake.main(
        [
            "--events-path",
            str(events_path),
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "candidate_narrative_intake_report.json").read_text())
    html = (tmp_path / "candidate_narrative_intake_report.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["event_count"] == 3
    assert payload["intake_review_queue"]["summary"]["action_required"] is True
    assert "<h1>候选叙事接入口报告</h1>" in html


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


def _event_payload() -> dict:
    return {
        "version": "candidate-narrative-events-v1",
        "events": [
            {
                "event_id": "EVT_MANUAL_ROBOT_001",
                "source_type": "manual",
                "event_time": "2026-05-28T09:30:00+08:00",
                "title": "机器人执行器产业链关注度上升",
                "summary": "多只机器人执行器相关股票被关注。",
                "source_name": "manual-research-note",
                "source_url": "manual://research/robot-actuator",
                "mentioned_stocks": [
                    {"stock_code": "300024", "stock_name": "机器人"},
                    {"stock_code": "688017", "stock_name": "绿的谐波"},
                ],
                "keywords": ["机器人", "执行器", "减速器"],
                "candidate_narratives": [
                    {
                        "name": "机器人执行器",
                        "canonical_taxonomy": "机器人",
                        "confidence": 0.64,
                    }
                ],
            },
            {
                "event_id": "EVT_NEWS_BAIJIU_001",
                "source_type": "news",
                "event_time": "2026-05-28T10:10:00+08:00",
                "title": "白酒龙头渠道调研更新",
                "summary": "高端白酒渠道库存和价格受到关注。",
                "source_name": "tushare-news-brief",
                "source_url": "https://example.test/news/baijiu",
                "mentioned_stocks": [{"stock_code": "600519", "stock_name": "贵州茅台"}],
                "keywords": ["白酒", "渠道", "消费"],
                "candidate_narratives": [
                    {
                        "narrative_id": "N_BAIJIU_CONSUMPTION",
                        "name": "高端白酒消费",
                        "confidence": 0.72,
                    }
                ],
            },
            {
                "event_id": "EVT_SOCIAL_ROBOT_001",
                "source_type": "social",
                "event_time": "2026-05-28T11:00:00+08:00",
                "title": "机器人执行器讨论升温",
                "summary": "社媒讨论重复出现执行器和减速器关键词。",
                "source_name": "social-sample",
                "source_url": "social://sample/robot-actuator",
                "mentioned_stocks": [{"stock_code": "300024", "stock_name": "机器人"}],
                "keywords": ["机器人", "执行器"],
                "candidate_narratives": [
                    {
                        "name": "机器人执行器",
                        "canonical_taxonomy": "机器人",
                        "confidence": 0.58,
                    }
                ],
            },
        ],
    }
