from src.providers.news import GoogleNewsRssEvidenceProvider
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


def _rss_feed(title: str = "Nvidia growth accelerates AI infrastructure - Example News") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>{title}</title>
      <link>https://example.com/news/1</link>
      <description>Profit growth and data center demand.</description>
      <pubDate>Thu, 14 May 2026 18:38:57 GMT</pubDate>
      <source>Example News</source>
    </item>
  </channel>
</rss>
"""
