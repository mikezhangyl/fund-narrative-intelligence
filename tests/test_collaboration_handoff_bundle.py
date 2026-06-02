from __future__ import annotations

import json

from scripts import run_collaboration_handoff_bundle
from src.scanners.collaboration_handoff_bundle import (
    build_collaboration_handoff_bundle,
    render_collaboration_handoff_html,
)


def test_handoff_bundle_packages_review_context_without_weakening_promotion_gates():
    bundle = build_collaboration_handoff_bundle(
        research_export=_research_export(),
        quality_audit=_quality_audit(),
        requested_decisions=_requested_decisions(),
        generated_at="2026-06-02T08:00:00+08:00",
    )

    assert bundle["version"] == "collaboration-handoff-bundle-v1"
    assert bundle["summary"] == {
        "candidate_count": 2,
        "evidence_count": 2,
        "note_count": 1,
        "quality_finding_count": 1,
        "requested_decision_count": 2,
        "audit_event_count": 4,
    }
    assert bundle["role_model"] == {
        "mode": "local_placeholder",
        "roles": ["reviewer", "pm", "architect", "operator"],
        "external_identity_provider_required": False,
    }
    assert bundle["governance_policy"] == {
        "promotion_gate_weakened": False,
        "evidence_required_for_promotion": True,
        "notes_can_promote_trusted_state": False,
        "chat_history_required": False,
    }
    assert bundle["requested_decisions"][0]["responsible_role"] == "reviewer"
    assert bundle["audit_trail"][0]["event_type"] == "bundle_created"
    serialized = json.dumps(bundle, ensure_ascii=False)
    assert "super-secret" not in serialized


def test_handoff_bundle_html_is_chinese_and_lists_decisions():
    html = render_collaboration_handoff_html(
        build_collaboration_handoff_bundle(
            research_export=_research_export(),
            quality_audit=_quality_audit(),
            requested_decisions=_requested_decisions(),
        )
    )

    assert "<h1>协作评审交接包</h1>" in html
    assert "不依赖聊天记录" in html
    assert "DECIDE-1" in html
    assert "reviewer" in html


def test_handoff_bundle_cli_reads_inputs_and_writes_json_html(tmp_path):
    research_path = tmp_path / "research.json"
    quality_path = tmp_path / "quality.json"
    decisions_path = tmp_path / "decisions.json"
    output_dir = tmp_path / "handoff"
    research_path.write_text(json.dumps(_research_export(), ensure_ascii=False), encoding="utf-8")
    quality_path.write_text(json.dumps(_quality_audit(), ensure_ascii=False), encoding="utf-8")
    decisions_path.write_text(json.dumps({"requested_decisions": _requested_decisions()}, ensure_ascii=False), encoding="utf-8")

    exit_code = run_collaboration_handoff_bundle.main(
        [
            "--research-export",
            str(research_path),
            "--quality-audit",
            str(quality_path),
            "--decisions",
            str(decisions_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    payload = json.loads((output_dir / "collaboration_handoff_bundle.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["requested_decision_count"] == 2
    assert "<h1>协作评审交接包</h1>" in (
        output_dir / "collaboration_handoff_bundle.html"
    ).read_text()


def _research_export() -> dict[str, object]:
    return {
        "version": "narrative-research-export-pack-v1",
        "narratives": ["AI", "算力"],
        "source_events": [
            {"source_event_id": "EVT-1", "title": "AI filing"},
            {"source_event_id": "EVT-2", "title": "算力公告"},
        ],
        "analyst_notes": [
            {
                "note_id": "NOTE-1",
                "linked_object_ref": {"object_type": "narrative", "object_id": "AI"},
                "body": "需要复核证据。",
                "promotion_effect": "none",
            }
        ],
    }


def _quality_audit() -> dict[str, object]:
    return {
        "issues": [
            {
                "issue_code": "LOW_SOURCE_DIVERSITY",
                "narrative_id": "N_AI",
                "quality_score": 79.2,
            }
        ],
        "secret": "super-secret-token",
    }


def _requested_decisions() -> list[dict[str, object]]:
    return [
        {
            "decision_id": "DECIDE-1",
            "decision_type": "accept_candidate",
            "target_ref": {"object_type": "narrative", "object_id": "AI"},
            "responsible_role": "reviewer",
            "rationale": "证据链完整，等待二次确认。",
        },
        {
            "decision_id": "DECIDE-2",
            "decision_type": "request_architect_review",
            "target_ref": {"object_type": "quality_finding", "object_id": "LOW_SOURCE_DIVERSITY"},
            "responsible_role": "architect",
            "rationale": "需要确认质量阈值。",
        },
    ]
