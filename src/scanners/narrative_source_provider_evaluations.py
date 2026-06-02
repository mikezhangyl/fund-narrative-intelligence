from __future__ import annotations

from typing import Any


def licensed_provider_evaluation(provider_id: str) -> dict[str, Any]:
    return _licensed_provider_evaluation_packs()[provider_id]


def _licensed_provider_evaluation_packs() -> dict[str, dict[str, Any]]:
    return {
        "wind_financial_terminal": _evaluation_pack(
            trial_contact_path="Apply for trial / sales contact through Wind product pages or Service@wind.com.cn.",
            api_availability="Wind Client API and enterprise data API are advertised for accessing Wind financial data.",
            cost_contract_notes="Enterprise contract required; pricing and news entitlements require sales confirmation.",
            market_coverage="China-first with global market, macro, industry, security, fund, and news coverage.",
            dataset_categories=["raw_news", "market_data_context", "filings", "broker_research"],
            official_source_links=[
                _link("Wind Financial Terminal", "https://www.wind.com.cn/portal/zh/WFT/index.html"),
                _link("Wind Client API", "https://www.wind.com.cn/mobile/ClientApi/zh.html"),
                _link("Wind Data API service", "https://www.wind.com.cn/mobile/WDS/sapi/zh.html"),
            ],
        ),
        "choice_financial_terminal": _evaluation_pack(
            trial_contact_path="Contact Choice data service at choiceinfo@eastmoney.com or 400-620-1818.",
            api_availability="Choice Quant API is advertised with function-call access and Python/C++ support.",
            cost_contract_notes="Contract package required; confirm news, research, and API quota entitlements.",
            market_coverage="China-first terminal and data service across stocks, funds, bonds, macro, industry, and company data.",
            dataset_categories=["market_data_context", "raw_news", "broker_research", "filings"],
            official_source_links=[
                _link("Choice data terminal and API", "https://choice.eastmoney.com/"),
            ],
        ),
        "ifind_financial_terminal": _evaluation_pack(
            trial_contact_path="Use iFinD partner/cooperation channel first; PM must obtain vendor contact and package details.",
            api_availability="iFinD quant/data API documentation exists; exact package and entitlement require vendor confirmation.",
            cost_contract_notes="Enterprise contract required; confirm Linux/API availability and news/research entitlements.",
            market_coverage="China-first institutional financial data, terminal, research, macro, and alternative-data cooperation.",
            dataset_categories=["market_data_context", "raw_news", "broker_research"],
            official_source_links=[
                _link("iFinD partner platform", "https://partners.51ifind.com/"),
                _link("iFinD quant API FAQ", "https://quantapi.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/faq.html"),
            ],
        ),
        "lseg_reuters_news": _evaluation_pack(
            trial_contact_path="Request details / free trial through LSEG product and developer portal pages.",
            api_availability="Reuters/LSEG News Service supports structured JSON, streaming, and request-response API surfaces.",
            cost_contract_notes="Enterprise contract and entitlement required; archives and redistribution terms must be confirmed.",
            market_coverage="Global Reuters and third-party news with metadata, topic codes, timestamps, sentiment, and significance.",
            dataset_categories=["raw_news", "machine_readable_news", "event_sentiment_analytics"],
            official_source_links=[
                _link("LSEG News Service developer portal", "https://developers.lseg.com/en/product/news/news_service_rdp"),
                _link("LSEG Real Time News", "https://www.lseg.com/en/data-analytics/financial-data/financial-news-coverage/political-news-feeds-analysis/real-time-news"),
            ],
        ),
        "ravenpack_news_analytics": _evaluation_pack(
            trial_contact_path="Request a trial from RavenPack News Analytics product page.",
            api_availability="News analytics product provides entity/event analytics; API/package details require trial confirmation.",
            cost_contract_notes="Enterprise contract required; confirm source coverage, history, redistribution, and usage limits.",
            market_coverage="Global news and social-media analytics with relevance, novelty, sentiment, topic, and event scoring.",
            dataset_categories=["machine_readable_news", "event_sentiment_analytics", "raw_news"],
            official_source_links=[
                _link("RavenPack News Analytics", "https://www.ravenpack.com/products/edge/data/news-analytics"),
            ],
        ),
        "alphasense_market_intelligence": _evaluation_pack(
            trial_contact_path="Contact AlphaSense sales/support; API docs say to reach apisupport@alphasense.com to begin a trial.",
            api_availability="AlphaSense developer docs describe API access; platform also lists ingestion API/connectors.",
            cost_contract_notes="Subscription/package required; confirm API availability, content export rights, and broker research access.",
            market_coverage="Global market intelligence: filings, transcripts, broker research, expert calls, news, trade journals, and regulatory documents.",
            dataset_categories=["transcripts", "broker_research", "filings", "raw_news"],
            official_source_links=[
                _link("AlphaSense contact", "https://www.alpha-sense.com/contact/"),
                _link("AlphaSense API docs", "https://developer.alpha-sense.com/api/next/getting-started/"),
                _link("AlphaSense pricing/content overview", "https://prod.alpha-sense.com/pricing/"),
            ],
        ),
        "benzinga_news": _evaluation_pack(
            trial_contact_path="Email licensing@benzinga.com, call 877-440-9464, or request access from Benzinga API pages.",
            api_availability="REST, TCP push, websocket, and documented newsfeed endpoints are available by subscription.",
            cost_contract_notes="Subscription/API key required; confirm redistribution, display rights, and endpoint entitlements.",
            market_coverage="North America-focused market news, stock news, transcripts, press releases, SEC filings, and alternative datasets.",
            dataset_categories=["raw_news", "transcripts", "filings"],
            official_source_links=[
                _link("Benzinga APIs", "https://www.benzinga.com/apis"),
                _link("Benzinga News API docs", "https://docs.benzinga.com/api-reference/news-api/overview"),
                _link("Benzinga Stock News API", "https://www.benzinga.com/apis/in/cloud-product/stock-news-api/"),
            ],
        ),
        "finnhub_news": _evaluation_pack(
            trial_contact_path="Start from Finnhub self-serve API key and pricing page; contact sales for production tiers.",
            api_availability="Documented REST market-news endpoint and SDK examples are available.",
            cost_contract_notes="Published self-serve and paid tiers exist; confirm news and transcript permissions for production use.",
            market_coverage="Global market API with news, filings, transcripts, fundamentals, estimates, and alternative data depending on tier.",
            dataset_categories=["raw_news", "transcripts", "filings", "market_data_context"],
            official_source_links=[
                _link("Finnhub home", "https://finnhub.io/"),
                _link("Finnhub market news API docs", "https://www.finnhub.io/docs/api/market-news"),
                _link("Finnhub pricing", "https://api.finnhub.io/pricing"),
            ],
        ),
        "tushare_news_permissions": _evaluation_pack(
            trial_contact_path="PM must verify Tushare account score/permission and whether target news endpoints are enabled.",
            api_availability="Tushare Pro API availability is score/permission gated by endpoint.",
            cost_contract_notes="Permission points and frequency tiers apply; endpoint-specific news rights need live smoke confirmation.",
            market_coverage="China market data community/API; news availability depends on endpoint permission.",
            dataset_categories=["raw_news", "market_data_context"],
            official_source_links=[
                _link("Tushare permission model", "https://tushare.pro/document/1?doc_id=108"),
            ],
        ),
    }


def _evaluation_pack(
    *,
    trial_contact_path: str,
    api_availability: str,
    cost_contract_notes: str,
    market_coverage: str,
    dataset_categories: list[str],
    official_source_links: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "trial_contact_path": trial_contact_path,
        "api_availability": api_availability,
        "cost_contract_notes": cost_contract_notes,
        "market_coverage": market_coverage,
        "dataset_categories": dataset_categories,
        "official_source_links": official_source_links,
    }


def _link(title: str, url: str) -> dict[str, str]:
    return {"title": title, "url": url}
