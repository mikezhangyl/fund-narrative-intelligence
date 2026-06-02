from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

_TEXT_DISPLAY = {
    "Trial First": "优先试用",
    "Later": "稍后评估",
    "Analytics Candidate": "新闻分析候选",
    "Do Not Implement": "暂不实现",
    "Controlled Pilot": "受控试点",
    "High-risk/Do Not Crawl": "高风险/不要爬取",
    "Unknown": "未确认",
    "Official API": "官方 API",
    "Commercial Access": "商业授权",
    "vendor_quote_required": "需要供应商报价",
    "endpoint entitlement list": "端点授权清单",
    "qps/rate limit": "QPS 与限流规则",
    "historical depth": "历史深度",
    "redistribution/display terms": "转发与展示条款",
    "cost band/vendor quote": "成本区间或供应商报价",
    "credentialed API docs": "需凭证访问的 API 文档",
    "news entitlement package": "新闻权限包",
    "credentialed docs": "需凭证访问的文档",
    "trial credentials": "试用凭证",
    "production pricing": "生产价格",
    "redistribution/display rights": "转发与展示权利",
    "China coverage sample": "中国覆盖样例",
    "Credentials, API docs, entitlement package, redistribution terms, and vendor quote are required.": (
        "需要凭证、接口文档、授权包、转发条款和供应商报价。"
    ),
    "Provider docs, credentials, entitled endpoints, and display/redistribution rights are required.": (
        "需要供应商文档、凭证、已授权端点，以及展示与转发权利。"
    ),
    "No crawler implementation until permission, robots/TOS, login, anti-bot, and retention status are confirmed.": (
        "在权限、robots/服务条款、登录、反爬和留存状态确认前，不做爬虫实现。"
    ),
}


def build_source_investigation_gate_pack(
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    sections = [_mik_240(), _mik_241(), _mik_242()]
    candidates = [
        candidate
        for section in sections
        for candidate in _list(section.get("candidates"))
    ]
    return {
        "version": "source-investigation-gate-pack-v1",
        "generated_at": generated_at or _utc_now(),
        "status": "completed",
        "summary": {
            "issue_count": len(sections),
            "candidate_count": len(candidates),
            "trial_first_count": sum(
                1 for candidate in candidates if candidate.get("decision_label") == "Trial First"
            ),
            "controlled_pilot_count": sum(
                1 for candidate in candidates if candidate.get("decision_label") == "Controlled Pilot"
            ),
            "developer_blocked_count": sum(
                1
                for section in sections
                if _mapping(section.get("developer_gate")).get("implementation_issue_allowed")
                is False
            ),
        },
        "decision_principles": [
            "Do not assign gateway/provider implementation until credentials, vendor docs, and rights metadata exist.",
            "Do not crawl login-only, CAPTCHA-protected, or anti-bot-heavy community pages.",
            "Social/community sources remain heat_signal_only and never trusted_fact.",
        ],
        "issue_sections": sections,
    }


def render_source_investigation_gate_pack_html(pack: dict[str, Any]) -> str:
    summary = _mapping(pack.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>R13 来源调查准入包</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>R13 来源调查准入包</h1>",
            '<section class="summary">',
            _html_kv("需求数", summary.get("issue_count")),
            _html_kv("候选来源", summary.get("candidate_count")),
            _html_kv("优先试用", summary.get("trial_first_count")),
            _html_kv("受控试点", summary.get("controlled_pilot_count")),
            _html_kv("开发接入暂不派发", summary.get("developer_blocked_count")),
            "<p>决策过程：公开官方信息只能形成试用准入判断，不足以派发供应商适配器实现；缺少凭证、合同、权限、转发与展示条款时，开发接入暂不派发。</p>",
            "</section>",
            *[_section_html(_mapping(section)) for section in _list(pack.get("issue_sections"))],
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _mik_240() -> dict[str, Any]:
    return {
        "linear_id": "MIK-240",
        "title": "China paid provider trial checklist: iFinD, Choice, Wind",
        "developer_gate": _developer_blocked_gate(
            "Credentials, API docs, entitlement package, redistribution terms, and vendor quote are required."
        ),
        "recommendation": {
            "decision": "trial_first",
            "trial_target": "choice_financial_terminal",
            "reason": (
                "Choice has public contact/API evidence and cross-platform Python/C++ support; "
                "PM still needs vendor quote, redistribution terms, and credentialed docs."
            ),
        },
        "candidates": [
            {
                "source_id": "choice_financial_terminal",
                "name": "Choice",
                "decision_label": "Trial First",
                "contact_trial_path": "choiceinfo@eastmoney.com / 400-620-1818",
                "api_availability": "Choice Quant API; official page lists Python, C++, C#, R, Matlab support and Linux/Mac support for C++/Python.",
                "endpoint_categories": [
                    "news",
                    "announcements/disclosures",
                    "research/briefs",
                    "sector/concept events",
                    "company events",
                    "macro/policy data",
                    "entity tags",
                ],
                "expected_coverage": "China market terminal/data service; exact news/research endpoint coverage requires vendor package.",
                "qps_rate_limit": "vendor_docs_required",
                "historical_depth": "vendor_docs_required",
                "redistribution_terms": "vendor_contract_required",
                "cost_band": "vendor_quote_required",
                "missing_information": _paid_provider_missing_info(),
                "official_source_links": [
                    _link("Choice data terminal/API", "https://choice.eastmoney.com/"),
                    _link("Choice Quant API login/docs", "https://quantapi.eastmoney.com/Flow?from=web"),
                ],
            },
            {
                "source_id": "wind_financial_terminal",
                "name": "Wind",
                "decision_label": "Later",
                "contact_trial_path": "Service@wind.com.cn / +86 400-820-9463 / +86 021-20518200",
                "api_availability": "Wind Client API and data API pages advertise API access to Wind data.",
                "endpoint_categories": [
                    "news",
                    "announcements/disclosures",
                    "research/briefs",
                    "sector/concept events",
                    "company events",
                    "macro/policy data",
                    "entity tags",
                ],
                "expected_coverage": "China-first terminal with global company, market, sector, macro, fund, and news coverage by package.",
                "qps_rate_limit": "vendor_docs_required",
                "historical_depth": "vendor_docs_required",
                "redistribution_terms": "vendor_contract_required",
                "cost_band": "vendor_quote_required",
                "missing_information": [
                    "news entitlement package",
                    "redistribution/display terms",
                    "cost band/vendor quote",
                    "credentialed API docs",
                ],
                "official_source_links": [
                    _link("Wind Client API", "https://www.wind.com.cn/mobile/ClientApi/zh.html"),
                    _link("Wind Data API", "https://www.wind.com.cn/mobile/WDS/sapi/zh.html"),
                ],
            },
            {
                "source_id": "ifind_financial_terminal",
                "name": "iFinD",
                "decision_label": "Later",
                "contact_trial_path": "PM vendor/contact confirmation required; public partner/API pages exist.",
                "api_availability": "iFinD quant/data API docs describe SDK/HTTP API access; package availability needs vendor confirmation.",
                "endpoint_categories": [
                    "news",
                    "research/briefs",
                    "sector/concept events",
                    "company events",
                    "macro/policy data",
                    "entity tags",
                ],
                "expected_coverage": "China institutional financial data, intelligent news/event processing, industrial chain and research datasets.",
                "qps_rate_limit": "vendor_docs_required",
                "historical_depth": "vendor_docs_required",
                "redistribution_terms": "vendor_contract_required",
                "cost_band": "vendor_quote_required",
                "missing_information": _paid_provider_missing_info(),
                "official_source_links": [
                    _link("iFinD platform", "https://aifind.com/"),
                    _link("iFinD partner platform", "https://partners.51ifind.com/"),
                    _link("iFinD quant API FAQ", "https://quantapi.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/faq.html"),
                ],
            },
        ],
    }


def _mik_241() -> dict[str, Any]:
    return {
        "linear_id": "MIK-241",
        "title": "Global paid news analytics trial checklist",
        "developer_gate": _developer_blocked_gate(
            "Provider docs, credentials, entitled endpoints, and display/redistribution rights are required."
        ),
        "recommendation": {
            "decision": "ranked_trial_targets",
            "professional_news_candidate": "lseg_reuters_news",
            "news_analytics_candidate": "ravenpack_news_analytics",
            "lower_cost_developer_api_candidate": "benzinga_news_api",
            "reason": "Use LSEG/Reuters for professional raw/news service, RavenPack for event analytics, and Benzinga as a lower-cost developer API candidate.",
        },
        "trial_smoke_query_set": {
            "symbols": ["AAPL", "NVDA", "TSLA", "BABA", "TSM"],
            "topics": ["AI semiconductors", "China EV", "Fed policy", "supply chain disruption"],
            "window": "last_24h_and_last_7d",
            "required_fields": [
                "headline",
                "published_at",
                "source",
                "entity_metadata",
                "sentiment_or_event_metadata",
                "permitted_url_or_story_id",
            ],
        },
        "candidates": [
            _global_candidate(
                "lseg_reuters_news",
                "LSEG / Reuters",
                "Trial First",
                "Request details/free trial through LSEG News Service pages.",
                "Structured JSON news service; streaming and request-response API surfaces.",
                "topic codes, timestamps, PermID, relevance/confidence, sentiment, significance, dedupe",
                "Reuters and third-party global news; China coverage depends on package.",
                ["https://developers.lseg.com/en/product/news/news_service_rdp", "https://www.lseg.com/en/data-analytics/financial-data/financial-news-coverage/news-coverage/"],
            ),
            _global_candidate(
                "ravenpack_news_analytics",
                "RavenPack / Bigdata.com",
                "Analytics Candidate",
                "Request a trial from RavenPack News Analytics.",
                "Analytics/data product; API/package details require trial confirmation.",
                "event/entity metadata, relevance, novelty, sentiment, topic tagging",
                "40,000+ news/social sources with multi-language global coverage; China coverage needs trial sample.",
                ["https://www.ravenpack.com/products/edge/data/news-analytics"],
            ),
            _global_candidate(
                "alphasense_market_intelligence",
                "AlphaSense",
                "Later",
                "Contact sales/support; API docs direct API trial setup through AlphaSense support.",
                "Developer docs describe GraphQL/API access and ingestion/connectors.",
                "search/document metadata; event/sentiment support not proven from public docs",
                "Filings, transcripts, broker research, expert calls, news, trade journals, regulatory docs.",
                ["https://www.alpha-sense.com/contact/", "https://developer.alpha-sense.com/api/next/getting-started"],
            ),
            _global_candidate(
                "benzinga_news_api",
                "Benzinga",
                "Trial First",
                "Email licensing@benzinga.com, call 877-440-9464, or request API access.",
                "REST, TCP push, websocket, and documented newsfeed endpoints.",
                "ticker/source/news metadata; sentiment/event analytics require endpoint confirmation",
                "North America-focused news, transcripts, filings, alternative datasets.",
                ["https://www.benzinga.com/apis", "https://docs.benzinga.com/introduction/introduction"],
            ),
            _global_candidate(
                "finnhub_news_api",
                "Finnhub",
                "Later",
                "Self-serve API key/pricing, contact sales for production permissions.",
                "Documented market-news REST endpoint.",
                "news endpoint metadata; filings/transcripts available depending on tier",
                "Global market APIs with news, filings, transcripts, fundamentals, estimates by tier.",
                ["https://www.finnhub.io/docs/api/market-news", "https://api.finnhub.io/pricing"],
            ),
        ],
    }


def _mik_242() -> dict[str, Any]:
    return {
        "linear_id": "MIK-242",
        "title": "China community and social source access investigation",
        "developer_gate": _developer_blocked_gate(
            "No crawler implementation until permission, robots/TOS, login, anti-bot, and retention status are confirmed."
        ),
        "recommendation": {
            "decision": "controlled_pilot_only_for_weibo_official_api",
            "reason": (
                "Only official API/commercial access can enter a controlled heat-signal pilot; "
                "Xueqiu and EastMoney Guba should not be crawled until permission is confirmed."
            ),
        },
        "candidates": [
            _social_candidate(
                "xueqiu",
                "雪球",
                "High-risk/Do Not Crawl",
                "No official heat-signal API confirmed from public review.",
                "login/terms risk; do not crawl until commercial/API permission exists",
                ["https://xueqiu.com/about/terms", "https://xueqiu.com/about/faq"],
            ),
            _social_candidate(
                "eastmoney_guba",
                "东方财富股吧",
                "Unknown",
                "Public community pages exist; no provider-neutral official API confirmed.",
                "community/TOS and anti-bot risk require PM legal/vendor review",
                ["https://guba.eastmoney.com/", "https://about.eastmoney.com/home/protocol"],
            ),
            _social_candidate(
                "weibo",
                "微博",
                "Official API",
                "Official API path exists, but finance-topic access, rate limits, retention, and display terms need confirmation.",
                "official API only; no browser scraping",
                ["https://docs.x.com/developer-guidelines", "https://docs.x.com/x-api/fundamentals/rate-limits"],
            ),
            _social_candidate(
                "stocktwits_reference",
                "Stocktwits reference pattern",
                "Commercial Access",
                "Use as a global reference pattern for heat-only access where official/commercial access exists.",
                "commercial or official API only",
                ["https://finnhub.io/"],
            ),
        ],
    }


def _global_candidate(
    source_id: str,
    name: str,
    decision_label: str,
    trial_path: str,
    api_access: str,
    metadata_support: str,
    coverage: str,
    links: list[str],
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "name": name,
        "decision_label": decision_label,
        "trial_path": trial_path,
        "api_access": api_access,
        "metadata_support": metadata_support,
        "chinese_china_coverage": coverage,
        "latency": "trial_required",
        "historical_archive": "trial_or_vendor_docs_required",
        "pricing_model": "vendor_quote_or_self_serve_tier_required",
        "redistribution_display_rights": "vendor_contract_required",
        "missing_information": [
            "credentialed docs",
            "trial credentials",
            "production pricing",
            "redistribution/display rights",
            "China coverage sample",
        ],
        "official_source_links": [_link(f"{name} source {index + 1}", url) for index, url in enumerate(links)],
    }


def _social_candidate(
    source_id: str,
    name: str,
    access_label: str,
    permission_status: str,
    risk_notes: str,
    links: list[str],
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "name": name,
        "access_label": access_label,
        "decision_label": "Controlled Pilot" if access_label == "Official API" else "Do Not Implement",
        "permission_status": permission_status,
        "anti_bot_risk": "medium" if access_label in {"Official API", "Commercial Access"} else "high",
        "retention_display_restrictions": "must be confirmed before pilot",
        "risk_notes": risk_notes,
        "output_role": "heat_signal_only",
        "trust_tier": "heat_signal_only",
        "controlled_pilot_allowed": access_label == "Official API",
        "official_source_links": [_link(f"{name} source {index + 1}", url) for index, url in enumerate(links)],
    }


def _paid_provider_missing_info() -> list[str]:
    return [
        "endpoint entitlement list",
        "qps/rate limit",
        "historical depth",
        "redistribution/display terms",
        "cost band/vendor quote",
        "credentialed API docs",
    ]


def _developer_blocked_gate(reason: str) -> dict[str, Any]:
    return {
        "implementation_issue_allowed": False,
        "reason": reason,
        "next_owner": "PM/vendor_contact_then_gateway",
    }


def _section_html(section: dict[str, Any]) -> str:
    rows = [_mapping(candidate) for candidate in _list(section.get("candidates"))]
    recommendation = _mapping(section.get("recommendation"))
    parts = [
        f"<section><h2>{_html_text(section.get('linear_id'))}: {_html_text(_display_title(section.get('title')))}</h2>",
        f"<p><strong>建议:</strong> {_html_text(_recommendation_text(recommendation))}</p>",
        f"<p><strong>开发接入暂不派发:</strong> {_html_text(_display_text(_mapping(section.get('developer_gate')).get('reason')))}</p>",
        _candidate_table(rows),
        "</section>",
    ]
    return "".join(parts)


def _candidate_table(rows: list[dict[str, Any]]) -> str:
    columns = (
        ("source_id", "来源ID"),
        ("name", "名称"),
        ("decision_label", "决策标签"),
        ("access_label", "访问标签"),
        ("cost_band", "成本口径"),
        ("missing_information", "缺口信息"),
    )
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_html_text(_display_text(_cell(row.get(column))))}</td>" for column, _ in columns)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _display_title(value: Any) -> str:
    return {
        "China paid provider trial checklist: iFinD, Choice, Wind": "中国付费数据服务试用清单：iFinD、Choice、Wind",
        "Global paid news analytics trial checklist": "全球付费新闻与新闻分析试用清单",
        "China community and social source access investigation": "中国社区与社交来源准入调查",
    }.get(str(value or ""), str(value or ""))


def _recommendation_text(recommendation: dict[str, Any]) -> str:
    decision = str(recommendation.get("decision") or "")
    if decision == "trial_first":
        return "优先试用 Choice。公开联系路径与 API 能力证据较清楚，但 PM 仍需补齐供应商报价、转发条款和需凭证访问的文档。"
    if decision == "ranked_trial_targets":
        return "全球付费新闻按三类推进：LSEG / Reuters 用于专业原始新闻，RavenPack 用于事件分析，Benzinga 作为成本较低的开发者接口候选。"
    if decision == "controlled_pilot_only_for_weibo_official_api":
        return "只有官方 API 或商业授权可进入受控热度信号试点；雪球与东方财富股吧在权限确认前不做爬虫实现。"
    return _display_text(recommendation)


def _display_text(value: Any) -> str:
    if isinstance(value, list):
        return "，".join(_display_text(item) for item in value)
    text = str(value or "")
    return _TEXT_DISPLAY.get(text, text)


def _cell(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _link(title: str, url: str) -> dict[str, str]:
    return {"title": title, "url": url}


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f7f8fa; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1240px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; margin-top: 12px; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; font-size: 13px; }
th { background: #eef2f7; color: #323f4b; }
""".strip()
