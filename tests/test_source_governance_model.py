from __future__ import annotations

import json

from scripts import run_source_governance_report as report_script
from src.scanners.source_governance import (
    evaluate_source_registry,
    load_source_governance_policy,
    validate_source_registry_entry,
)


def _entry(**overrides):
    entry = {
        "source_id": "sec_edgar_filings",
        "display_name": "SEC EDGAR filings",
        "acquisition_mode": "official_api",
        "permission_status": "public_official",
        "license_scope": "metadata_and_public_document_reference",
        "retention_policy": "metadata_and_permitted_excerpt",
        "redistribution_policy": "link_and_metadata_only",
        "anti_bot_risk": "low",
        "owner_service": "stock-data-gateway",
        "robots_tos_review": {
            "status": "not_required_official_api",
            "reviewed_at": "2026-06-01",
            "reviewer": "Architect",
        },
        "request_pacing_policy": {
            "status": "defined",
            "max_requests_per_minute": 10,
            "cache_ttl_seconds": 3600,
        },
        "prohibited_behaviors": [],
        "allowed_product_use": ["trusted_fact_candidate"],
    }
    return {**entry, **overrides}


def test_source_governance_policy_declares_required_fields_and_prohibitions():
    policy = load_source_governance_policy()

    assert policy["version"] == "narrative-source-governance-v1"
    assert set(policy["required_registry_fields"]) >= {
        "permission_status",
        "license_scope",
        "retention_policy",
        "redistribution_policy",
        "anti_bot_risk",
        "owner_service",
    }
    assert set(policy["prohibited_behaviors"]) >= {
        "captcha_bypass",
        "stealth_browser",
        "residential_proxy_evasion",
        "credential_sharing",
        "login_only_scraping_without_permission",
    }


def test_valid_official_source_registry_entry_passes_governance():
    decision = validate_source_registry_entry(_entry())

    assert decision["gate_status"] == "passed"
    assert decision["missing_required_fields"] == []
    assert decision["blocked_reasons"] == []
    assert decision["live_smoke_allowed"] is True


def test_crawler_source_requires_robots_tos_review_and_pacing_before_smoke():
    decision = validate_source_registry_entry(
        _entry(
            source_id="industry_media_public_page",
            acquisition_mode="public_web_crawler",
            robots_tos_review={"status": "not_reviewed"},
            request_pacing_policy={"status": "missing"},
        )
    )

    assert decision["gate_status"] == "blocked"
    assert decision["live_smoke_allowed"] is False
    assert "robots_tos_review_required" in decision["blocked_reasons"]
    assert "request_pacing_policy_required" in decision["blocked_reasons"]


def test_prohibited_behaviors_block_source_entry():
    decision = validate_source_registry_entry(
        _entry(prohibited_behaviors=["captcha_bypass", "credential_sharing"])
    )

    assert decision["gate_status"] == "blocked"
    assert decision["live_smoke_allowed"] is False
    assert decision["prohibited_behavior_hits"] == [
        "captcha_bypass",
        "credential_sharing",
    ]


def test_source_governance_report_outputs_json_and_chinese_html(tmp_path):
    input_path = tmp_path / "source_registry.json"
    input_path.write_text(
        json.dumps(
            {
                "version": "test-source-registry-v1",
                "sources": [
                    _entry(),
                    _entry(
                        source_id="blocked_crawler",
                        display_name="Blocked crawler",
                        acquisition_mode="public_web_crawler",
                        robots_tos_review={"status": "not_reviewed"},
                        request_pacing_policy={"status": "missing"},
                    ),
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = report_script.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 1
    payload = json.loads((tmp_path / "out" / "source_governance_report.json").read_text())
    html = (tmp_path / "out" / "source_governance_report.html").read_text()

    assert payload["summary"]["source_count"] == 2
    assert payload["summary"]["blocked_count"] == 1
    assert payload["decisions"][0]["live_smoke_allowed"] is True
    assert "来源准入治理报告" in html
    assert "blocked_crawler" in html
    assert "robots_tos_review_required" in html
    assert "CAPTCHA" in html


def test_evaluate_source_registry_counts_blocked_and_passed_sources():
    registry = {"sources": [_entry(), _entry(source_id="bad", owner_service="")]}

    evaluation = evaluate_source_registry(registry)

    assert evaluation["summary"]["source_count"] == 2
    assert evaluation["summary"]["passed_count"] == 1
    assert evaluation["summary"]["blocked_count"] == 1
