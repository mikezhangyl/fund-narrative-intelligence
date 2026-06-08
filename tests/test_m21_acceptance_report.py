from __future__ import annotations

import json

from scripts import run_m21_acceptance_report
from src.scanners.m21_acceptance_report import (
    build_m21_acceptance_report,
    render_m21_acceptance_report_html,
)


def test_m21_acceptance_report_cites_artifacts_and_separates_statuses():
    report = build_m21_acceptance_report(
        artifacts=_artifacts(),
        verification_commands=_commands(),
        generated_at="2026-06-08T10:20:00Z",
    )

    assert report["version"] == "m21-source-derived-candidate-acceptance-v1"
    assert report["decision"]["pm_architect_decision"] == "continue_with_warnings"
    assert report["decision"]["merge_language_zh"].startswith("建议进入下一轮")
    assert report["status_buckets"] == {
        "can_do": [
            "live_gateway_source_event_acceptance",
            "source_candidate_review_queue",
            "candidate_evidence_drilldown",
            "review_action_ledger",
            "operator_workflow",
        ],
        "fixture_only": [],
        "degraded": ["source_trust_preflight"],
        "blocked": [],
        "not_implemented": ["automatic_trusted_promotion"],
    }
    assert report["artifact_references"]["live_probe"]["path"].endswith("live_probe.json")
    assert report["verification_commands"] == _commands()
    assert report["coverage_matrix"]["source_kinds"] == [
        {"source_kind": "official_filings", "acceptance_status": "pass", "row_count": 2},
        {"source_kind": "social_heat", "acceptance_status": "degraded", "row_count": 0},
    ]
    assert report["coverage_matrix"]["candidate_states"] == [
        {"candidate_state": "candidate_untrusted", "count": 2}
    ]
    assert "SOCIAL_SOURCE_DISABLED" in report["known_degraded_sources"][0]["degradation_events"]
    assert all("predict" not in risk.lower() for risk in report["risks"])
    assert report["disclosure"]["trusted_or_predictive_claims_made"] is False


def test_m21_acceptance_report_html_is_chinese_and_has_decision_language():
    html = render_m21_acceptance_report_html(
        build_m21_acceptance_report(
            artifacts=_artifacts(),
            verification_commands=_commands(),
        )
    )

    assert "<h1>M21 来源候选叙事验收报告</h1>" in html
    assert "PM/Architect 决策" in html
    assert "Can-Do" in html
    assert "降级" in html
    assert "未实现" in html
    assert "live_probe.json" in html
    assert "不构成投资建议" in html
    assert "不会声称候选叙事已经可信或可预测" in html


def test_m21_acceptance_report_cli_writes_json_and_html(tmp_path):
    paths = {}
    for name, payload in _artifact_payloads().items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        paths[name] = path

    exit_code = run_m21_acceptance_report.main(
        [
            "--live-probe",
            str(paths["live_probe"]),
            "--fixture-probe",
            str(paths["fixture_probe"]),
            "--queue",
            str(paths["queue"]),
            "--evidence",
            str(paths["evidence"]),
            "--ledger",
            str(paths["ledger"]),
            "--preflight",
            str(paths["preflight"]),
            "--workflow",
            str(paths["workflow"]),
            "--verification-command",
            "uv run pytest tests/test_m21_acceptance_report.py -q",
            "--output-dir",
            str(tmp_path / "acceptance"),
        ]
    )

    payload = json.loads(
        (tmp_path / "acceptance" / "m21_acceptance_report.json").read_text()
    )
    html = (tmp_path / "acceptance" / "m21_acceptance_report.html").read_text()

    assert exit_code == 0
    assert payload["decision"]["pm_architect_decision"] == "continue_with_warnings"
    assert "<h1>M21 来源候选叙事验收报告</h1>" in html


def _commands() -> list[str]:
    return [
        "uv run pytest tests/test_m21_acceptance_report.py -q",
        "uv run ruff check scripts/run_m21_acceptance_report.py src/scanners/m21_acceptance_report.py tests/test_m21_acceptance_report.py",
    ]


def _artifacts() -> dict[str, dict[str, object]]:
    payloads = _artifact_payloads()
    return {
        name: {"path": f"outputs/m21/{name}.json", "payload": payload}
        for name, payload in payloads.items()
    }


def _artifact_payloads() -> dict[str, dict[str, object]]:
    return {
        "live_probe": {
            "summary": {"blocking_source_kinds": 0, "acceptance_status_counts": {"pass": 1, "degraded": 1}},
            "source_results": [
                {"source_kind": "official_filings", "acceptance_status": "pass", "row_count": 2, "degradation_events": []},
                {"source_kind": "social_heat", "acceptance_status": "degraded", "row_count": 0, "degradation_events": ["SOCIAL_SOURCE_DISABLED"]},
            ],
        },
        "fixture_probe": {
            "summary": {"blocking_source_kinds": 0, "acceptance_status_counts": {"pass": 2}},
            "source_results": [],
        },
        "queue": {
            "summary": {"visible_count": 2, "trusted_count": 0},
            "rows": [
                {"candidate_id": "CAND_AI", "candidate_state": "candidate_untrusted"},
                {"candidate_id": "CAND_HEAT", "candidate_state": "candidate_untrusted"},
            ],
        },
        "evidence": {"summary": {"source_event_count": 2, "missing_event_count": 0}},
        "ledger": {"summary": {"total_action_count": 1, "trusted_action_count": 0}},
        "preflight": {"overall_status": "warning"},
        "workflow": {"summary": {"digest_item_count": 2, "linked_candidate_count": 2, "trusted_item_count": 0}},
    }
