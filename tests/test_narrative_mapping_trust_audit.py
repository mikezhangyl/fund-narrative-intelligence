from __future__ import annotations

import json

from scripts import run_narrative_mapping_trust_audit
from src.scanners.narrative_mapping_trust_audit import (
    execute_narrative_mapping_trust_audit,
    render_html_report,
)


def test_narrative_mapping_trust_audit_blocks_untrusted_seed_stores():
    report = execute_narrative_mapping_trust_audit(
        registry_payload=_registry_payload(),
        mapping_payload=_mapping_payload(),
    )

    assert report["status"] == "blocked"
    assert report["summary"] == {
        "narrative_count": 2,
        "mapping_count": 2,
        "blocker_count": 5,
        "warning_count": 2,
        "trusted_mapping_count": 0,
    }
    assert "registry_untrusted_experimental" in report["blockers"]
    assert "mapping_store_untrusted_experimental" in report["blockers"]
    assert "mapping_source_evidence_missing:2" in report["blockers"]
    assert "mapping_formal_rationale_missing:2" in report["blockers"]
    assert report["mapping_audit"]["undefined_narrative_ids"] == ["N_UNKNOWN"]
    assert report["promotion_decision"] == {
        "can_promote_to_trusted": False,
        "required_next_step": "source_and_logic_audit",
    }


def test_narrative_mapping_trust_audit_html_contains_methodology_sections():
    report = execute_narrative_mapping_trust_audit(
        registry_payload=_registry_payload(),
        mapping_payload=_mapping_payload(),
    )

    html = render_html_report(report)

    assert "<h1>叙事映射可信度审计</h1>" in html
    assert "股票事实层" in html
    assert "候选叙事生成" in html
    assert "映射打分" in html
    assert "反例和排除" in html
    assert "人工审核入口" in html


def test_run_narrative_mapping_trust_audit_writes_json_and_html(tmp_path):
    registry_path = tmp_path / "registry.json"
    mapping_path = tmp_path / "mappings.json"
    registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
    mapping_path.write_text(json.dumps(_mapping_payload()), encoding="utf-8")

    exit_code = run_narrative_mapping_trust_audit.main(
        [
            "--registry-path",
            str(registry_path),
            "--mappings-path",
            str(mapping_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "narrative_mapping_trust_audit.json").read_text())
    html = (tmp_path / "narrative_mapping_trust_audit.html").read_text()

    assert exit_code == 1
    assert payload["status"] == "blocked"
    assert payload["summary"]["mapping_count"] == 2
    assert "<h1>叙事映射可信度审计</h1>" in html


def test_narrative_mapping_methodology_document_records_trust_bar():
    text = (
        run_narrative_mapping_trust_audit.METHODOLOGY_PATH.read_text(encoding="utf-8")
    )

    assert "Narrative Mapping Methodology v0" in text
    assert "candidate_untrusted" in text
    assert "trusted_validated" in text
    assert "反例和排除" in text


def _registry_payload() -> dict:
    return {
        "version": "registry-v1",
        "trust_metadata": {
            "trust_status": "untrusted_experimental",
            "trust_note": "seed registry",
        },
        "narratives": [
            {
                "narrative_id": "N_AI_INFRA",
                "display_name": "AI 基础设施",
                "human_review_status": "approved",
                "reviewed_by": "seed-curation",
                "reviewed_at": "2026-05-15",
            },
            {
                "narrative_id": "N_BAIJIU_CONSUMPTION",
                "display_name": "高端白酒消费",
                "human_review_status": "approved",
                "reviewed_by": "seed-curation",
                "reviewed_at": "2026-05-15",
            },
        ],
    }


def _mapping_payload() -> dict:
    return {
        "version": "mapping-v1",
        "trust_metadata": {
            "trust_status": "untrusted_experimental",
            "trust_note": "seed mappings",
        },
        "mappings": [
            {
                "stock_code": "NVDA",
                "narrative_id": "N_AI_INFRA",
                "mapping_weight": 0.9,
                "confidence": 0.86,
                "method": "reviewed_mapping",
                "review": {"status": "approved"},
            },
            {
                "stock_code": "000063",
                "narrative_id": "N_UNKNOWN",
                "mapping_weight": 0.5,
                "confidence": 0.82,
                "method": "reviewed_mapping",
                "review": {"status": "approved"},
            },
        ],
    }
