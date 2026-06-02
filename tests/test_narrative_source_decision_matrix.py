from __future__ import annotations

import json

from scripts import run_narrative_source_decision_matrix
from src.scanners.narrative_source_decision_matrix import (
    build_narrative_source_decision_matrix,
    render_narrative_source_decision_matrix_html,
)


def test_source_decision_matrix_covers_r13_source_groups_and_boundaries():
    matrix = build_narrative_source_decision_matrix(
        generated_at="2026-06-02T10:30:00+00:00",
    )

    assert matrix["version"] == "narrative-source-decision-matrix-v1"
    assert matrix["generated_at"] == "2026-06-02T10:30:00+00:00"
    assert matrix["summary"] == {
        "source_group_count": 4,
        "provider_count": 21,
        "can_do_or_crawl_pilot_count": 8,
        "paid_trial_count": 8,
        "pm_investigation_required_count": 12,
        "avoid_count": 1,
    }
    assert matrix["consumer_policy"] == {
        "provider_access_allowed": False,
        "provider_integration_owner": "stock-data-gateway",
        "fni_role": "display_decision_matrix_and_consume_governed_source_events",
        "social_sources_fact_promotion_allowed": False,
        "license_metadata_required": True,
    }
    assert matrix["crawler_policy"] == {
        "no_captcha_bypass": True,
        "no_stealth_browser": True,
        "no_proxy_evasion": True,
        "no_login_only_content": True,
        "robots_tos_review_required": True,
        "request_pacing_required": True,
        "content_hash_required": True,
        "dedupe_required": True,
    }

    groups = {group["group_id"]: group for group in matrix["source_groups"]}
    assert set(groups) == {
        "licensed_news_market_intelligence",
        "official_disclosure_regulator",
        "public_web_industry_media",
        "community_social_heat",
    }
    assert groups["licensed_news_market_intelligence"]["boundary_decision"] == (
        "third_party_paid_provider_owned_until_gateway_contract"
    )
    assert groups["official_disclosure_regulator"]["boundary_decision"] == "gateway_owned"
    assert groups["public_web_industry_media"]["decision_label"] == "Crawl Pilot"
    assert groups["community_social_heat"]["output_role"] == "heat_signal_only"


def test_provider_rows_encode_permissions_owner_and_non_dev_ready_gates():
    matrix = build_narrative_source_decision_matrix()
    providers = {
        provider["provider_id"]: provider
        for group in matrix["source_groups"]
        for provider in group["providers"]
    }

    assert providers["cninfo_announcements"]["decision_label"] == "Can-Do"
    assert providers["cninfo_announcements"]["owner_service"] == "stock-data-gateway"
    assert providers["cninfo_announcements"]["trust_tier"] == "trusted_fact"
    assert providers["sec_edgar"]["decision_label"] == "Can-Do"
    assert providers["sec_edgar"]["integration_path"] == (
        "Gateway source-events adapter already smoke-tested; FNI consumes governed source events."
    )
    assert providers["wind_financial_terminal"]["decision_label"] == "Paid Trial"
    assert providers["wind_financial_terminal"]["dev_ready"] is False
    assert providers["wind_financial_terminal"]["blocking_gate"] == "PM investigation required"
    assert providers["ravenpack_news_analytics"]["recommended_trial_role"] == (
        "global_news_analytics_candidate_pending_pm_trial"
    )
    assert providers["x_public_social"]["decision_label"] == "Backlog"
    assert providers["x_public_social"]["anti_bot_risk"] == "high"
    assert providers["captcha_or_login_only_pages"]["decision_label"] == "Avoid"
    assert providers["captcha_or_login_only_pages"]["dev_ready"] is False


def test_licensed_provider_evaluation_pack_has_trial_api_contract_and_source_links():
    matrix = build_narrative_source_decision_matrix()
    licensed_group = next(
        group
        for group in matrix["source_groups"]
        if group["group_id"] == "licensed_news_market_intelligence"
    )

    for provider in licensed_group["providers"]:
        evaluation = provider["evaluation_pack"]

        assert evaluation["trial_contact_path"]
        assert evaluation["api_availability"]
        assert evaluation["cost_contract_notes"]
        assert evaluation["market_coverage"]
        assert set(evaluation["dataset_categories"]).issubset(
            {
                "raw_news",
                "machine_readable_news",
                "event_sentiment_analytics",
                "transcripts",
                "broker_research",
                "filings",
                "market_data_context",
            }
        )
        assert evaluation["official_source_links"]
        assert all(link["url"].startswith("https://") for link in evaluation["official_source_links"])

    providers = {provider["provider_id"]: provider for provider in licensed_group["providers"]}

    assert "Client API" in providers["wind_financial_terminal"]["evaluation_pack"]["api_availability"]
    assert "choiceinfo@eastmoney.com" in (
        providers["choice_financial_terminal"]["evaluation_pack"]["trial_contact_path"]
    )
    assert "apisupport@alphasense.com" in (
        providers["alphasense_market_intelligence"]["evaluation_pack"]["trial_contact_path"]
    )
    assert providers["benzinga_news"]["evaluation_pack"]["dataset_categories"] == [
        "raw_news",
        "transcripts",
        "filings",
    ]
    assert providers["finnhub_news"]["evaluation_pack"]["cost_contract_notes"] == (
        "Published self-serve and paid tiers exist; confirm news and transcript permissions for production use."
    )


def test_architecture_contract_is_explicit_enough_for_next_implementation():
    contract = build_narrative_source_decision_matrix()["architecture_contract"]

    assert contract["source_event_v2_required_fields"] == [
        "source_event_id",
        "source_id",
        "source_group",
        "source_url",
        "published_at",
        "retrieved_at",
        "entity_refs",
        "event_type",
        "raw_title",
        "permitted_excerpt",
        "language",
        "trust_tier",
        "license_scope",
        "retention_policy",
        "acquisition_run_id",
        "content_hash",
        "degraded_reason",
    ]
    assert contract["narrative_fact_required_fields"] == [
        "fact_id",
        "source_event_id",
        "claim_text",
        "entity_refs",
        "fact_time",
        "confidence_label",
        "review_status",
    ]
    assert contract["candidate_narrative_required_fields"] == [
        "candidate_narrative_id",
        "title",
        "theme",
        "supporting_source_event_ids",
        "heat_signal_ids",
        "trusted_fact_count",
        "freshness_bucket",
        "promotion_status",
    ]
    assert contract["verification_gates"] == [
        "live_smoke",
        "schema_drift_check",
        "dedupe_check",
        "source_quality_report",
        "degraded_semantics_check",
    ]


def test_source_decision_matrix_html_is_chinese_and_names_boundaries():
    html = render_narrative_source_decision_matrix_html(
        build_narrative_source_decision_matrix()
    )

    assert "<h1>叙事来源决策矩阵</h1>" in html
    assert "不绕过 CAPTCHA" in html
    assert "Gateway-owned" in html
    assert "PM investigation required" in html
    assert "Provider trial/API 评估" in html
    assert "choiceinfo@eastmoney.com" in html
    assert "apisupport@alphasense.com" in html
    assert "社交/社区仅作为热度或候选信号" in html
    assert "FNI 不直接访问 provider" in html


def test_source_decision_matrix_cli_writes_json_and_html(tmp_path):
    output_dir = tmp_path / "matrix"

    exit_code = run_narrative_source_decision_matrix.main(
        ["--output-dir", str(output_dir)]
    )
    payload = json.loads((output_dir / "narrative_source_decision_matrix.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["source_group_count"] == 4
    assert payload["consumer_policy"]["provider_access_allowed"] is False
    assert "<h1>叙事来源决策矩阵</h1>" in (
        output_dir / "narrative_source_decision_matrix.html"
    ).read_text()
