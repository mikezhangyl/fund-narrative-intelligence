from src.providers.news import (
    GoogleNewsRssEvidenceProvider,
    MultiSourceNewsEvidenceProvider,
    SinaFinanceRollNewsProvider,
    StcnFinanceNewsProvider,
)
from src.validation import validate_news_evidence_payload


def test_google_news_rss_provider_converts_feed_items_to_evidence():
    provider = GoogleNewsRssEvidenceProvider(fetcher=lambda _url: _rss_feed())

    payload = provider.get_news_evidence(
        narratives=[
            {
                "narrative_id": "N_AI_INFRA",
                "name": "AI Infrastructure",
                "aliases": ["accelerated computing"],
            }
        ],
        as_of_date="2026-05-14",
    )

    validate_news_evidence_payload(payload)
    assert payload["provider_name"] == "google-news-rss"
    assert payload["data_quality"] == "fresh"
    assert payload["query_scope"] == {
        "requested_narrative_ids": ["N_AI_INFRA"],
        "queried_narrative_ids": ["N_AI_INFRA"],
        "omitted_narrative_ids": [],
        "query_limit": 4,
    }
    assert payload["evidence"][0]["narrative_id"] == "N_AI_INFRA"
    assert payload["evidence"][0]["source"] == "google_news_rss"
    assert payload["evidence"][0]["sentiment"] == "positive"
    assert "article body content was not parsed" in payload["evidence"][0]["summary"]


def test_google_news_rss_provider_filters_stale_items():
    provider = GoogleNewsRssEvidenceProvider(
        fetcher=lambda _url: _rss_feed(pub_date="Thu, 07 Jul 2022 18:38:57 GMT")
    )

    payload = provider.get_news_evidence(
        narratives=[
            {
                "narrative_id": "N_AI_INFRA",
                "name": "AI Infrastructure",
                "aliases": ["accelerated computing"],
            }
        ],
        as_of_date="2026-05-15",
    )

    validate_news_evidence_payload(payload)
    assert payload["evidence"] == []
    assert payload["missing_narrative_ids"] == ["N_AI_INFRA"]
    assert payload["skipped_item_count"] == 1


def test_google_news_rss_provider_records_degraded_narratives():
    def fetcher(url: str) -> str:
        if "AI" in url:
            raise RuntimeError("rate limited")
        return _rss_feed(title="Healthcare risk warning - Example News")

    provider = GoogleNewsRssEvidenceProvider(fetcher=fetcher)

    payload = provider.get_news_evidence(
        narratives=[
            {"narrative_id": "N_AI_INFRA", "name": "AI Infrastructure"},
            {"narrative_id": "N_HEALTHCARE", "name": "Healthcare Innovation"},
        ],
        as_of_date="2026-05-14",
    )

    assert payload["data_quality"] == "partial"
    assert payload["missing_narrative_ids"] == ["N_AI_INFRA"]
    assert payload["query_scope"]["queried_narrative_ids"] == ["N_HEALTHCARE"]
    assert payload["degradation_events"][0]["provider_name"] == "google-news-rss"
    assert payload["evidence"][0]["sentiment"] == "negative"


def test_news_evidence_validation_accepts_non_google_provider_contract():
    payload = GoogleNewsRssEvidenceProvider(fetcher=lambda _url: _rss_feed()).get_news_evidence(
        narratives=[{"narrative_id": "N_AI_INFRA", "name": "AI Infrastructure"}],
        as_of_date="2026-05-14",
    )
    payload["provider_name"] = "generic-news-provider"
    payload["provider_version"] = "generic-news-v1"

    validate_news_evidence_payload(payload)


def test_sina_finance_roll_provider_filters_headlines_by_narrative_keywords():
    provider = SinaFinanceRollNewsProvider(fetcher=lambda _url: _sina_roll_html())

    payload = provider.get_news_evidence(
        narratives=[
            {
                "narrative_id": "N_HK_TECH_PLATFORMS",
                "name": "Hong Kong Tech Platforms",
                "aliases": ["Hang Seng Tech"],
                "related_terms": ["腾讯控股", "阿里巴巴", "港股科技"],
            }
        ],
        as_of_date="2026-05-15",
    )

    validate_news_evidence_payload(payload)
    assert payload["provider_name"] == "sina-finance-roll"
    assert payload["data_quality"] == "fresh"
    assert payload["evidence"][0]["source"] == "sina_finance_roll"
    assert payload["evidence"][0]["title"] == "腾讯发布AI工具升级，港股科技平台再受关注"
    assert payload["evidence"][0]["sentiment"] == "mixed"


def test_multi_source_news_provider_merges_google_and_sina_evidence():
    provider = MultiSourceNewsEvidenceProvider(
        providers=(
            GoogleNewsRssEvidenceProvider(fetcher=lambda _url: _rss_feed()),
            SinaFinanceRollNewsProvider(fetcher=lambda _url: _sina_roll_html()),
        )
    )

    payload = provider.get_news_evidence(
        narratives=[
            {
                "narrative_id": "N_HK_TECH_PLATFORMS",
                "name": "Hong Kong Tech Platforms",
                "aliases": ["Hang Seng Tech"],
                "related_terms": ["腾讯控股", "阿里巴巴", "港股科技"],
            }
        ],
        as_of_date="2026-05-15",
    )

    validate_news_evidence_payload(payload)
    assert payload["provider_name"] == "multi-source-news"
    assert payload["data_quality"] == "fresh"
    assert len(payload["evidence"]) == 2
    assert sorted({item["source"] for item in payload["evidence"]}) == [
        "google_news_rss",
        "sina_finance_roll",
    ]


def test_stcn_provider_filters_headlines_by_narrative_keywords():
    provider = StcnFinanceNewsProvider(fetcher=lambda _url: _stcn_html())

    payload = provider.get_news_evidence(
        narratives=[
            {
                "narrative_id": "N_AI_INFRA",
                "name": "AI Infrastructure",
                "aliases": ["accelerated computing"],
                "related_terms": ["算力", "数据中心", "AI"],
            }
        ],
        as_of_date="2026-05-15",
    )

    validate_news_evidence_payload(payload)
    assert payload["provider_name"] == "stcn-finance"
    assert payload["data_quality"] == "fresh"
    assert payload["evidence"][0]["source"] == "stcn_finance"
    assert payload["evidence"][0]["title"] == "AI仍是核心主线！外资：关注应用落地与基础设施"
    assert payload["evidence"][0]["sentiment"] == "mixed"


def test_multi_source_news_provider_tracks_cross_source_corroboration():
    provider = MultiSourceNewsEvidenceProvider(
        providers=(
            GoogleNewsRssEvidenceProvider(
                fetcher=lambda _url: _rss_feed(
                    title="AI仍是核心主线！外资：关注应用落地与基础设施",
                    pub_date="Fri, 15 May 2026 08:00:00 GMT",
                )
            ),
            SinaFinanceRollNewsProvider(fetcher=lambda _url: _sina_roll_html()),
            StcnFinanceNewsProvider(fetcher=lambda _url: _stcn_html()),
        )
    )

    payload = provider.get_news_evidence(
        narratives=[
            {
                "narrative_id": "N_AI_INFRA",
                "name": "AI Infrastructure",
                "aliases": ["accelerated computing"],
                "related_terms": ["基础设施", "算力", "AI"],
            }
        ],
        as_of_date="2026-05-15",
    )

    validate_news_evidence_payload(payload)
    assert payload["provider_name"] == "multi-source-news"
    assert payload["data_quality"] == "fresh"
    assert len(payload["evidence"]) == 2
    corroborated = next(
        item
        for item in payload["evidence"]
        if item["title"] == "AI仍是核心主线！外资：关注应用落地与基础设施"
    )
    assert corroborated["corroboration_count"] == 2
    assert sorted(corroborated["corroborating_source_providers"]) == [
        "google-news-rss",
        "stcn-finance",
    ]
    assert "cross-source corroboration" in corroborated["classification_reason"]


def _rss_feed(
    title: str = "Nvidia growth accelerates AI infrastructure - Example News",
    pub_date: str = "Thu, 14 May 2026 18:38:57 GMT",
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>{title}</title>
      <link>https://example.com/news/1</link>
      <description>Profit growth and data center demand.</description>
      <pubDate>{pub_date}</pubDate>
      <source>Example News</source>
    </item>
  </channel>
</rss>
"""


def _sina_roll_html() -> str:
    return """
<html>
  <body>
    <a href="https://finance.sina.com.cn/stock/hkstock/2026-05-15/doc-example1.shtml">
      腾讯发布AI工具升级，港股科技平台再受关注
    </a>
    <a href="https://finance.sina.com.cn/stock/hkstock/2026-05-15/doc-example2.shtml">
      银行板块分红预期升温
    </a>
  </body>
</html>
"""


def _stcn_html() -> str:
    return """
<html>
  <body>
    <a href="https://www.stcn.com/article/detail/2155538.html">
      AI仍是核心主线！外资：关注应用落地与基础设施
    </a>
    <a href="/article/detail/2155539.html">
      银行板块分红预期升温
    </a>
    <a href="https://xp.stcn.com/notice/detail/1.html">
      公司公告
    </a>
  </body>
</html>
"""
