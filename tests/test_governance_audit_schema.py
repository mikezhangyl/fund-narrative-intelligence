from __future__ import annotations

import json
from pathlib import Path

from src.scanners.governance_audit import (
    build_governance_audit_export,
    load_governance_audit_schema,
    render_html_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_governance_audit_schema_declares_record_types_and_flattening_rules():
    schema = load_governance_audit_schema()

    assert schema["version"] == "governance-audit-schema-v1"
    assert set(schema["record_types"]) == {
        "narrative",
        "candidate_narrative",
        "stock_mapping",
        "candidate_mapping",
        "evidence_pack",
        "promotion_decision",
    }
    assert "trust_status" in schema["required_trust_state_fields"]
    assert schema["csv_flattening"]["list_separator"] == " | "
    assert schema["read_only"] is True


def test_governance_audit_flags_promoted_records_without_service_ledger_approval():
    export = build_governance_audit_export(
        record_payload=_record_payload(),
        service_ledger_payload=_service_ledger_payload(),
    )

    assert export["version"] == "governance-audit-export-v1"
    assert export["read_only"] is True
    assert export["summary"]["record_count"] == 3
    assert export["summary"]["pm_facing_warning_count"] == 1
    assert export["summary"]["developer_facing_warning_count"] == 1
    flagged = [record for record in export["records"] if record["warning_codes"]]
    assert flagged[0]["record_id"] == "N_PROMOTED_LOCAL_ONLY"
    assert flagged[0]["pm_facing_warnings"] == [
        "Promoted-looking record lacks service-ledger approval."
    ]
    assert flagged[0]["developer_facing_warnings"] == [
        "missing_service_ledger_approval"
    ]
    assert flagged[0]["csv_flat"]["warning_codes"] == "missing_service_ledger_approval"


def test_governance_audit_html_is_chinese_table_output():
    export = build_governance_audit_export(
        record_payload=_record_payload(),
        service_ledger_payload=_service_ledger_payload(),
    )

    html = render_html_report(export)

    assert "<h1>叙事治理审计导出</h1>" in html
    assert "记录类型" in html
    assert "PM 可见告警" in html
    assert "missing_service_ledger_approval" in html


def _record_payload() -> dict:
    return json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "governance_audit_records.v1.json")
        .read_text(encoding="utf-8")
    )


def _service_ledger_payload() -> dict:
    return {
        "version": "service-ledger-approvals-v1",
        "approved_record_ids": ["N_APPROVED_IN_LEDGER"],
    }
