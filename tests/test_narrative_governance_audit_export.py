from __future__ import annotations

import json
from pathlib import Path

from scripts import run_narrative_governance_audit_export
from src.scanners.narrative_governance_audit_export import (
    build_narrative_governance_audit_export,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_narrative_governance_audit_export_includes_governance_health_fields():
    export = build_narrative_governance_audit_export(
        registry_payload=_registry_payload(),
        service_ledger_payload={"approved_record_ids": ["N_LEDGER_APPROVED"]},
    )

    assert export["version"] == "governance-audit-export-v1"
    assert export["read_only"] is True
    first = export["records"][0]
    assert first["record_id"] == "N_LOCAL_PROMOTED"
    assert first["source_count"] == 2
    assert first["review_status"] == "approved"
    assert first["promotion_decision"] == "promoted_without_service_ledger"
    assert first["missing_gates"] == ["service_ledger_approval"]
    assert first["latest_reviewer"] == "codex-review"
    assert first["warning_codes"] == ["missing_service_ledger_approval"]
    assert first["csv_flat"]["missing_gates"] == "service_ledger_approval"


def test_run_narrative_governance_audit_export_writes_json_and_html(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_narrative_governance_audit_export.main(
        [
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "narrative_governance_audit_export.json").read_text())
    html = (tmp_path / "narrative_governance_audit_export.html").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["summary"]["record_count"] == 3
    assert "叙事治理审计导出" in html
    assert "missing_service_ledger_approval" in html


def _registry_payload() -> dict:
    return json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "narrative_governance_registry.v1.json")
        .read_text(encoding="utf-8")
    )
