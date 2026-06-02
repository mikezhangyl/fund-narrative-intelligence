from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.narrative_source_provider_evaluations import (
    licensed_provider_evaluation,
)


def build_narrative_source_decision_matrix(
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    source_groups = _source_groups()
    providers = [
        provider
        for group in source_groups
        for provider in _list(group.get("providers"))
    ]
    return {
        "version": "narrative-source-decision-matrix-v1",
        "generated_at": generated_at or _utc_now(),
        "status": "completed",
        "summary": {
            "source_group_count": len(source_groups),
            "provider_count": len(providers),
            "can_do_or_crawl_pilot_count": _count_labels(
                providers,
                {"Can-Do", "Crawl Pilot"},
            ),
            "paid_trial_count": _count_labels(providers, {"Paid Trial"}),
            "pm_investigation_required_count": sum(
                1
                for provider in providers
                if provider.get("blocking_gate") == "PM investigation required"
            ),
            "avoid_count": _count_labels(providers, {"Avoid"}),
        },
        "consumer_policy": {
            "provider_access_allowed": False,
            "provider_integration_owner": "stock-data-gateway",
            "fni_role": "display_decision_matrix_and_consume_governed_source_events",
            "social_sources_fact_promotion_allowed": False,
            "license_metadata_required": True,
        },
        "crawler_policy": {
            "no_captcha_bypass": True,
            "no_stealth_browser": True,
            "no_proxy_evasion": True,
            "no_login_only_content": True,
            "robots_tos_review_required": True,
            "request_pacing_required": True,
            "content_hash_required": True,
            "dedupe_required": True,
        },
        "source_groups": source_groups,
        "architecture_contract": _architecture_contract(),
        "dev_ready_guidance": [
            {
                "linear_id": "MIK-221",
                "status": "dev_ready_for_decision_matrix",
                "next_owner": "FNI",
            },
            {
                "linear_id": "MIK-222",
                "status": "dev_ready_for_architecture_contract",
                "next_owner": "FNI",
            },
            {
                "linear_id": "MIK-224",
                "status": "pm_investigation_required_before_provider_integration",
                "next_owner": "PM",
            },
            {
                "linear_id": "MIK-225",
                "status": "gateway_can_start_official_source_contracts",
                "next_owner": "stock-data-gateway",
            },
            {
                "linear_id": "MIK-226",
                "status": "crawler_pilot_requires_robots_tos_review",
                "next_owner": "stock-data-gateway",
            },
            {
                "linear_id": "MIK-227",
                "status": "social_heat_requires_permission_review",
                "next_owner": "PM_then_gateway",
            },
        ],
    }


def render_narrative_source_decision_matrix_html(matrix: dict[str, Any]) -> str:
    summary = _mapping(matrix.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>叙事来源决策矩阵</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>叙事来源决策矩阵</h1>",
            '<section class="summary">',
            _html_kv("来源组", summary.get("source_group_count", 0)),
            _html_kv("Provider / source", summary.get("provider_count", 0)),
            _html_kv("Can-Do / Crawl Pilot", summary.get("can_do_or_crawl_pilot_count", 0)),
            _html_kv("Paid Trial", summary.get("paid_trial_count", 0)),
            _html_kv("PM investigation required", summary.get("pm_investigation_required_count", 0)),
            "<p>FNI 不直接访问 provider；Gateway-owned 的 acquisition 由 stock-data-gateway 负责，FNI 只展示决策矩阵并消费治理后的 source events。</p>",
            "<p>爬虫边界：不绕过 CAPTCHA，不使用 stealth browser，不做 proxy evasion，不采集 login-only 内容。</p>",
            "<p>社交/社区仅作为热度或候选信号，不能在没有 trusted fact 支撑时 promoted 为事实。</p>",
            "</section>",
            _groups_table(_list(matrix.get("source_groups"))),
            _providers_table(_list(matrix.get("source_groups"))),
            _licensed_evaluation_table(_list(matrix.get("source_groups"))),
            _contract_table(_mapping(matrix.get("architecture_contract"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _source_groups() -> list[dict[str, Any]]:
    return [
        {
            "group_id": "licensed_news_market_intelligence",
            "name_zh": "付费新闻与市场情报",
            "decision_label": "Paid Trial",
            "boundary_decision": "third_party_paid_provider_owned_until_gateway_contract",
            "owner_service": "PM_then_stock-data-gateway",
            "output_role": "timely_news_or_news_analytics",
            "integration_path": "PM completes trial/contact/API-doc review; gateway then owns adapter and live smoke.",
            "providers": [
                _provider(
                    "wind_financial_terminal",
                    "Wind",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "timely_news_research_context",
                    "contract_required",
                    "medium",
                    blocking_gate="PM investigation required",
                    dataset_notes="raw news, disclosures, terminal research context depending on licensed package",
                    recommended_trial_role="china_first_candidate_pending_pm_trial",
                    evaluation_pack=licensed_provider_evaluation("wind_financial_terminal"),
                    dev_ready=False,
                ),
                _provider(
                    "choice_financial_terminal",
                    "Choice",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "timely_news_research_context",
                    "contract_required",
                    "medium",
                    blocking_gate="PM investigation required",
                    dataset_notes="China market news and terminal datasets pending PM package review",
                    recommended_trial_role="china_first_candidate_pending_pm_trial",
                    evaluation_pack=licensed_provider_evaluation("choice_financial_terminal"),
                    dev_ready=False,
                ),
                _provider(
                    "ifind_financial_terminal",
                    "iFinD",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "timely_news_research_context",
                    "contract_required",
                    "medium",
                    blocking_gate="PM investigation required",
                    dataset_notes="China market terminal/news package pending PM trial checklist",
                    recommended_trial_role="china_first_candidate_pending_pm_trial",
                    evaluation_pack=licensed_provider_evaluation("ifind_financial_terminal"),
                    dev_ready=False,
                ),
                _provider(
                    "lseg_reuters_news",
                    "LSEG / Reuters News API",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "raw_news",
                    "contract_required",
                    "low",
                    blocking_gate="PM investigation required",
                    dataset_notes="global raw news and licensed news API scope pending PM contact",
                    recommended_trial_role="global_raw_news_candidate_pending_pm_trial",
                    evaluation_pack=licensed_provider_evaluation("lseg_reuters_news"),
                    dev_ready=False,
                ),
                _provider(
                    "ravenpack_news_analytics",
                    "RavenPack / Bigdata.com",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "machine_readable_news_analytics",
                    "contract_required",
                    "low",
                    blocking_gate="PM investigation required",
                    dataset_notes="event/sentiment analytics scope pending PM trial package",
                    recommended_trial_role="global_news_analytics_candidate_pending_pm_trial",
                    evaluation_pack=licensed_provider_evaluation("ravenpack_news_analytics"),
                    dev_ready=False,
                ),
                _provider(
                    "alphasense_market_intelligence",
                    "AlphaSense",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "research_transcripts_context",
                    "contract_required",
                    "low",
                    blocking_gate="PM investigation required",
                    dataset_notes="transcripts, research, and market-intelligence scope pending contract review",
                    evaluation_pack=licensed_provider_evaluation("alphasense_market_intelligence"),
                    dev_ready=False,
                ),
                _provider(
                    "benzinga_news",
                    "Benzinga",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "timely_news",
                    "contract_required",
                    "low",
                    blocking_gate="PM investigation required",
                    dataset_notes="news API feasibility pending PM package review",
                    evaluation_pack=licensed_provider_evaluation("benzinga_news"),
                    dev_ready=False,
                ),
                _provider(
                    "finnhub_news",
                    "Finnhub",
                    "Paid Trial",
                    "PM_then_stock-data-gateway",
                    "timely_news",
                    "contract_required",
                    "low",
                    blocking_gate="PM investigation required",
                    dataset_notes="news API feasibility and permission tier pending PM review",
                    evaluation_pack=licensed_provider_evaluation("finnhub_news"),
                    dev_ready=False,
                ),
                _provider(
                    "tushare_news_permissions",
                    "Tushare news permissions",
                    "Backlog",
                    "PM_then_stock-data-gateway",
                    "timely_news",
                    "permission_required",
                    "medium",
                    blocking_gate="PM investigation required",
                    dataset_notes="requires PM permission/live-smoke investigation before integration",
                    evaluation_pack=licensed_provider_evaluation("tushare_news_permissions"),
                    dev_ready=False,
                ),
            ],
        },
        {
            "group_id": "official_disclosure_regulator",
            "name_zh": "官方披露与监管来源",
            "decision_label": "Can-Do",
            "boundary_decision": "gateway_owned",
            "owner_service": "stock-data-gateway",
            "output_role": "trusted_fact",
            "integration_path": "Gateway source-events adapters produce high-trust evidence events; FNI consumes governed outputs.",
            "providers": [
                _provider(
                    "cninfo_announcements",
                    "CNINFO announcements",
                    "Can-Do",
                    "stock-data-gateway",
                    "trusted_fact",
                    "public_disclosure_reference",
                    "low",
                    freshness_expectation="same_day_when_gateway_live",
                    identifier_mapping_need="A-share symbol, company name, announcement id",
                    retention_policy="metadata_and_permitted_excerpt",
                    integration_path="Gateway source-events adapter already smoke-tested; FNI consumes governed source events.",
                ),
                _provider(
                    "sec_edgar",
                    "SEC EDGAR",
                    "Can-Do",
                    "stock-data-gateway",
                    "trusted_fact",
                    "public_disclosure_reference",
                    "low",
                    freshness_expectation="same_day_when_gateway_live",
                    identifier_mapping_need="CIK, ticker, accession number",
                    retention_policy="metadata_and_permitted_excerpt",
                    integration_path="Gateway source-events adapter already smoke-tested; FNI consumes governed source events.",
                ),
                _provider(
                    "sse_szse_disclosures",
                    "SSE / SZSE disclosures",
                    "Crawl Pilot",
                    "stock-data-gateway",
                    "trusted_fact",
                    "public_disclosure_reference",
                    "low",
                    freshness_expectation="same_day_after_review",
                    identifier_mapping_need="exchange symbol, announcement id",
                    retention_policy="metadata_and_permitted_excerpt",
                ),
                _provider(
                    "hkex_disclosures",
                    "HKEX disclosures",
                    "Crawl Pilot",
                    "stock-data-gateway",
                    "trusted_fact",
                    "public_disclosure_reference",
                    "low",
                    freshness_expectation="same_day_after_review",
                    identifier_mapping_need="HK ticker, issuer id",
                    retention_policy="metadata_and_permitted_excerpt",
                ),
                _provider(
                    "company_ir_newsrooms",
                    "Company IR / newsroom pages",
                    "Crawl Pilot",
                    "stock-data-gateway",
                    "trusted_fact_or_context",
                    "public_page_reference_after_tos_review",
                    "medium",
                    freshness_expectation="daily_or_on_demand",
                    identifier_mapping_need="company domain, ticker, legal entity",
                    retention_policy="metadata_url_and_hash",
                ),
                _provider(
                    "policy_regulator_sites",
                    "Policy / regulator sites",
                    "Crawl Pilot",
                    "stock-data-gateway",
                    "trusted_fact_or_policy_context",
                    "public_page_reference_after_tos_review",
                    "low",
                    freshness_expectation="daily_or_weekly",
                    identifier_mapping_need="agency, policy topic, industry tags",
                    retention_policy="metadata_url_and_hash",
                ),
            ],
        },
        {
            "group_id": "public_web_industry_media",
            "name_zh": "公网行业媒体与静态页面",
            "decision_label": "Crawl Pilot",
            "boundary_decision": "gateway_owned",
            "owner_service": "stock-data-gateway",
            "output_role": "source_event_only",
            "integration_path": "Only public RSS/sitemaps/static pages with robots/TOS review, pacing, cache, hash, dedupe, and failure logging.",
            "providers": [
                _provider(
                    "rss_sitemap_public_pages",
                    "RSS / sitemap public pages",
                    "Crawl Pilot",
                    "stock-data-gateway",
                    "source_event_only",
                    "public_page_reference_after_tos_review",
                    "low",
                    retention_policy="metadata_url_excerpt_and_hash",
                ),
                _provider(
                    "industry_static_media",
                    "Industry vertical static media",
                    "Crawl Pilot",
                    "stock-data-gateway",
                    "source_event_only",
                    "public_page_reference_after_tos_review",
                    "medium",
                    retention_policy="metadata_url_excerpt_and_hash",
                ),
                _provider(
                    "captcha_or_login_only_pages",
                    "CAPTCHA / login-only protected pages",
                    "Avoid",
                    "none",
                    "none",
                    "not_allowed",
                    "critical",
                    blocking_gate="Not allowed by crawler policy",
                    dev_ready=False,
                    retention_policy="none",
                ),
            ],
        },
        {
            "group_id": "community_social_heat",
            "name_zh": "社区与社交热度",
            "decision_label": "Backlog",
            "boundary_decision": "gateway_owned_after_permission_review",
            "owner_service": "PM_then_stock-data-gateway",
            "output_role": "heat_signal_only",
            "integration_path": "Use only official API, licensed data, or clearly compliant low-risk public access; never promote chatter to fact without trusted evidence.",
            "providers": [
                _provider(
                    "stocktwits_social_heat",
                    "Stocktwits",
                    "Backlog",
                    "PM_then_stock-data-gateway",
                    "heat_signal_only",
                    "permission_required",
                    "medium",
                    blocking_gate="PM investigation required",
                    dataset_notes="mention count, entity mentions, topics, freshness, source health",
                    dev_ready=False,
                ),
                _provider(
                    "eastmoney_xueqiu_heat",
                    "EastMoney Guba / Xueqiu",
                    "Backlog",
                    "PM_then_stock-data-gateway",
                    "heat_signal_only",
                    "permission_required",
                    "high",
                    blocking_gate="PM investigation required",
                    dataset_notes="China community heat only after permission/risk status is clear",
                    dev_ready=False,
                ),
                _provider(
                    "x_public_social",
                    "X / Reddit / Weibo social heat",
                    "Backlog",
                    "PM_then_stock-data-gateway",
                    "heat_signal_only",
                    "permission_required",
                    "high",
                    blocking_gate="PM investigation required",
                    dataset_notes="official API/licensed/compliant access only; no stealth or proxy evasion",
                    dev_ready=False,
                ),
            ],
        },
    ]


def _provider(
    provider_id: str,
    name: str,
    decision_label: str,
    owner_service: str,
    output_role: str,
    license_scope: str,
    anti_bot_risk: str,
    *,
    trust_tier: str | None = None,
    dev_ready: bool = True,
    blocking_gate: str = "",
    dataset_notes: str = "",
    recommended_trial_role: str = "",
    freshness_expectation: str = "",
    identifier_mapping_need: str = "",
    retention_policy: str = "metadata_and_permitted_excerpt",
    integration_path: str = "",
    evaluation_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "name": name,
        "decision_label": decision_label,
        "owner_service": owner_service,
        "output_role": output_role,
        "trust_tier": trust_tier or _trust_tier(output_role),
        "license_scope": license_scope,
        "anti_bot_risk": anti_bot_risk,
        "dev_ready": dev_ready,
        "blocking_gate": blocking_gate,
        "dataset_notes": dataset_notes,
        "recommended_trial_role": recommended_trial_role,
        "freshness_expectation": freshness_expectation,
        "identifier_mapping_need": identifier_mapping_need,
        "retention_policy": retention_policy,
        "integration_path": integration_path or "Requires owner-specific adapter contract before implementation.",
        "evaluation_pack": evaluation_pack or {},
    }


def _architecture_contract() -> dict[str, Any]:
    return {
        "boundary_decisions": {
            "licensed_news_market_intelligence": "paid_provider_or_gateway_after_contract",
            "official_disclosure_regulator": "gateway_owned",
            "public_web_industry_media": "gateway_owned_crawl_pilot",
            "community_social_heat": "gateway_owned_after_permission_review",
            "fni": "consumer_display_only",
        },
        "source_registry_required_fields": [
            "source_id",
            "source_group",
            "permission_status",
            "license_scope",
            "freshness_sla",
            "trust_tier",
            "anti_bot_risk",
            "retry_policy",
            "cache_ttl",
            "owner_service",
            "gateway_boundary",
        ],
        "source_event_v2_required_fields": [
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
        ],
        "narrative_fact_required_fields": [
            "fact_id",
            "source_event_id",
            "claim_text",
            "entity_refs",
            "fact_time",
            "confidence_label",
            "review_status",
        ],
        "candidate_narrative_required_fields": [
            "candidate_narrative_id",
            "title",
            "theme",
            "supporting_source_event_ids",
            "heat_signal_ids",
            "trusted_fact_count",
            "freshness_bucket",
            "promotion_status",
        ],
        "verification_gates": [
            "live_smoke",
            "schema_drift_check",
            "dedupe_check",
            "source_quality_report",
            "degraded_semantics_check",
        ],
    }


def _trust_tier(output_role: str) -> str:
    if "trusted_fact" in output_role:
        return "trusted_fact"
    if output_role == "heat_signal_only":
        return "heat_signal_only"
    if output_role == "none":
        return "not_applicable"
    return "context_or_candidate"


def _count_labels(providers: list[dict[str, Any]], labels: set[str]) -> int:
    return sum(1 for provider in providers if provider.get("decision_label") in labels)


def _groups_table(groups: list[Any]) -> str:
    return _table(
        "来源组决策",
        [_mapping(group) for group in groups],
        ("group_id", "name_zh", "decision_label", "owner_service", "boundary_decision", "output_role"),
    )


def _providers_table(groups: list[Any]) -> str:
    providers = [
        provider
        for group in groups
        for provider in _list(_mapping(group).get("providers"))
    ]
    return _table(
        "Provider / source 评估",
        [_mapping(provider) for provider in providers],
        ("provider_id", "name", "decision_label", "owner_service", "output_role", "anti_bot_risk", "blocking_gate"),
    )


def _licensed_evaluation_table(groups: list[Any]) -> str:
    licensed_group = next(
        (
            _mapping(group)
            for group in groups
            if _mapping(group).get("group_id") == "licensed_news_market_intelligence"
        ),
        {},
    )
    rows = []
    for provider in _list(licensed_group.get("providers")):
        mapped = _mapping(provider)
        evaluation = _mapping(mapped.get("evaluation_pack"))
        rows.append(
            {
                "provider": mapped.get("name"),
                "trial_contact_path": evaluation.get("trial_contact_path"),
                "api_availability": evaluation.get("api_availability"),
                "cost_contract_notes": evaluation.get("cost_contract_notes"),
                "dataset_categories": ", ".join(
                    str(category) for category in _list(evaluation.get("dataset_categories"))
                ),
                "official_source_links": ", ".join(
                    str(_mapping(link).get("url"))
                    for link in _list(evaluation.get("official_source_links"))
                ),
            }
        )
    return _table(
        "Provider trial/API 评估",
        rows,
        (
            "provider",
            "trial_contact_path",
            "api_availability",
            "cost_contract_notes",
            "dataset_categories",
            "official_source_links",
        ),
    )


def _contract_table(contract: dict[str, Any]) -> str:
    rows = [
        {"field": key, "value": ", ".join(str(item) for item in value)}
        for key, value in contract.items()
        if isinstance(value, list)
    ]
    return _table("架构契约字段", rows, ("field", "value"))


def _table(title: str, rows: list[dict[str, Any]], columns: tuple[str, ...]) -> str:
    header = "".join(f"<th>{_html_text(column)}</th>" for column in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_html_text(row.get(column))}</td>" for column in columns)
        + "</tr>"
        for row in rows
    )
    return f"<section><h2>{_html_text(title)}</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f7f8fa; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1240px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; font-size: 13px; }
th { background: #eef2f7; color: #323f4b; }
""".strip()
