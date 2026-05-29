from __future__ import annotations

import json

from scripts import run_production_readiness_assistant
from src.scanners.production_readiness_assistant import (
    build_production_readiness_assistant,
    render_html_report,
)


def test_production_readiness_builds_health_freshness_ai_and_feedback_surfaces():
    report = build_production_readiness_assistant(
        payload=_production_payload(),
        as_of="2026-05-30T10:00:00+08:00",
        ai_enabled=True,
    )

    assert report["version"] == "production-readiness-assisted-intelligence-v1"
    assert report["summary"] == {
        "service_count": 3,
        "unhealthy_service_count": 1,
        "dataset_count": 4,
        "freshness_breach_count": 2,
        "runbook_action_count": 4,
        "ai_summary_count": 2,
        "feedback_count": 2,
        "open_feedback_count": 1,
    }
    assert report["services"][1]["health_status"] == "degraded"
    assert report["freshness"][0]["freshness_status"] == "fresh"
    assert report["freshness"][2]["freshness_status"] == "breached"
    assert report["freshness"][2]["breach"] is True
    assert report["ai_assistance"]["enabled"] is True
    assert report["ai_assistance"]["summaries"][0]["label"] == "AI assisted explanation"
    assert report["ai_assistance"]["summaries"][0]["citations"] == ["EV_AI_001", "SRC_AI_001"]
    assert report["ai_assistance"]["summaries"][0]["can_set_trust_state"] is False
    assert report["feedback"][0]["can_mutate_trusted_state"] is False
    assert report["feedback"][0]["audit_trail"][0]["action"] == "submitted"
    assert "api_key" not in json.dumps(report).lower()
    assert "secret" not in json.dumps(report).lower()


def test_ai_assistance_can_be_disabled_without_losing_contract_metadata():
    report = build_production_readiness_assistant(
        payload=_production_payload(),
        as_of="2026-05-30T10:00:00+08:00",
        ai_enabled=False,
    )

    assert report["ai_assistance"]["enabled"] is False
    assert report["ai_assistance"]["summaries"] == []
    assert report["ai_assistance"]["disabled_reason"] == "AI assistance disabled by operator setting."
    assert report["authoritative_sources"] == [
        "deterministic_scores",
        "source_evidence",
        "review_state",
        "promotion_ledger",
    ]


def test_production_readiness_html_is_chinese_and_shows_runbooks_and_sla():
    report = build_production_readiness_assistant(
        payload=_production_payload(),
        as_of="2026-05-30T10:00:00+08:00",
        ai_enabled=True,
    )

    html = render_html_report(report)

    assert "<h1>生产就绪与辅助智能看板</h1>" in html
    assert "数据新鲜度与 SLA" in html
    assert "Runbook 动作" in html
    assert "AI 辅助说明" in html
    assert "AI 不能设置评分、信任状态或推广状态" in html


def test_run_production_readiness_assistant_writes_json_and_html(tmp_path):
    fixture_path = tmp_path / "production.json"
    fixture_path.write_text(
        json.dumps(_production_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = run_production_readiness_assistant.main(
        [
            "--input-path",
            str(fixture_path),
            "--as-of",
            "2026-05-30T10:00:00+08:00",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "production_readiness_assistant.json").read_text())
    html = (tmp_path / "production_readiness_assistant.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["freshness_breach_count"] == 2
    assert payload["summary"]["ai_summary_count"] == 2
    assert "<h1>生产就绪与辅助智能看板</h1>" in html


def _production_payload() -> dict:
    return {
        "services": [
            {
                "service_id": "gateway",
                "display_name": "Market Data Gateway",
                "owner_service": "Gateway",
                "latest_run": {
                    "run_id": "gw-20260530",
                    "status": "succeeded",
                    "completed_at": "2026-05-30T09:55:00+08:00",
                    "artifact_refs": ["outputs/gateway/latest.json"],
                    "logs": {"api_key": "should-redact"},
                },
                "warnings": [],
                "runbooks": [
                    {"category": "data_gap", "title": "检查 provider 权限", "href": "docs/runbooks/gateway.md"}
                ],
            },
            {
                "service_id": "narrative-service",
                "display_name": "Narrative Service",
                "owner_service": "Narrative Service",
                "latest_run": {
                    "run_id": "ns-20260530",
                    "status": "warning",
                    "completed_at": "2026-05-30T09:40:00+08:00",
                    "artifact_refs": ["outputs/narrative/latest.json"],
                },
                "warnings": [{"category": "stale_evidence", "message": "two narratives stale"}],
                "runbooks": [
                    {"category": "stale_evidence", "title": "重跑质量审计", "href": "docs/runbooks/narrative.md"},
                    {"category": "provider_degraded", "title": "检查来源降级", "href": "docs/runbooks/provider.md"},
                ],
            },
            {
                "service_id": "fni",
                "display_name": "FNI reports",
                "owner_service": "FNI",
                "latest_run": {
                    "run_id": "fni-20260530",
                    "status": "failed",
                    "completed_at": "2026-05-30T08:50:00+08:00",
                    "artifact_refs": ["outputs/fni/latest.json"],
                },
                "warnings": [{"category": "report_failed", "message": "workspace report failed"}],
                "runbooks": [
                    {"category": "report_failed", "title": "查看报告失败排查", "href": "docs/runbooks/fni.md"}
                ],
            },
        ],
        "datasets": [
            _dataset("fund_holdings", "2026-05-30T09:50:00+08:00", 24, []),
            _dataset("narrative_radar", "2026-05-30T05:00:00+08:00", 2, ["delayed_run"]),
            _dataset("evidence_quality", "2026-05-28T09:00:00+08:00", 24, ["stale_evidence"]),
            _dataset("workspace_outputs", "2026-05-29T08:00:00+08:00", 12, ["report_failed"]),
        ],
        "ai_summary_inputs": [
            {
                "summary_id": "sum-ai-infra",
                "object_type": "narrative",
                "object_id": "N_AI_INFRA",
                "source_ids": ["SRC_AI_001"],
                "evidence_ids": ["EV_AI_001"],
                "score_component_ids": ["heat_score", "quality_score"],
                "text": "AI 基础设施热度来自多条已引用证据，但仍需人工复核。",
                "model": "disabled-safe-template",
                "prompt_version": "summary-v1",
            },
            {
                "summary_id": "sum-blockers",
                "object_type": "quality_audit",
                "object_id": "audit-20260530",
                "source_ids": ["SRC_QA_001"],
                "evidence_ids": ["EV_QA_001"],
                "score_component_ids": ["staleness", "source_diversity"],
                "text": "质量阻塞主要来自证据过期和来源集中。",
                "model": "disabled-safe-template",
                "prompt_version": "summary-v1",
            },
        ],
        "feedback": [
            {
                "feedback_id": "fb-001",
                "type": "bad_mapping",
                "severity": "high",
                "status": "open",
                "linked_object": {"type": "narrative_mapping", "id": "MAP_AI_001"},
                "reviewer": {"role": "operator", "display_name": "reviewer-a"},
            },
            {
                "feedback_id": "fb-002",
                "type": "confusing_summary",
                "severity": "medium",
                "status": "triaged",
                "linked_object": {"type": "ai_summary", "id": "sum-blockers"},
                "reviewer": {"role": "analyst", "display_name": "reviewer-b"},
            },
        ],
    }


def _dataset(
    dataset_id: str,
    source_timestamp: str,
    sla_target_hours: int,
    degraded_reasons: list[str],
) -> dict:
    return {
        "dataset_id": dataset_id,
        "surface": dataset_id.replace("_", " "),
        "source_timestamp": source_timestamp,
        "last_successful_run_at": source_timestamp,
        "sla_target_hours": sla_target_hours,
        "degraded_reasons": degraded_reasons,
    }
