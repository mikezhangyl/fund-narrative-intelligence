from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from src.config import DATA_QUALITY_CONFIDENCE
from src.validation import validate_news_evidence_payload

GOOGLE_NEWS_RSS_PROVIDER = "google-news-rss"
GOOGLE_NEWS_RSS_VERSION = "google-news-rss-v1"
GOOGLE_NEWS_RSS_SOURCE_URL = "https://news.google.com/rss/search"
SINA_FINANCE_ROLL_PROVIDER = "sina-finance-roll"
SINA_FINANCE_ROLL_VERSION = "sina-finance-roll-v1"
SINA_FINANCE_ROLL_SOURCE_URL = "https://finance.sina.com.cn/roll/"
STCN_FINANCE_PROVIDER = "stcn-finance"
STCN_FINANCE_VERSION = "stcn-finance-v1"
STCN_FINANCE_SOURCE_URL = "https://www.stcn.com/article/index.html"
MULTI_SOURCE_NEWS_PROVIDER = "multi-source-news"
MULTI_SOURCE_NEWS_VERSION = "multi-source-news-v1"
NEWS_EVIDENCE_VERSION = "news-evidence-v1"
NEWS_EVIDENCE_QUERY_LIMIT = 4
_MAX_NEWS_AGE_DAYS = 365

_POSITIVE_TERMS = (
    "growth",
    "surge",
    "beat",
    "record",
    "profit",
    "upgrade",
    "expands",
    "wins",
    "增长",
    "创新高",
    "盈利",
    "上调",
    "中标",
)
_NEGATIVE_TERMS = (
    "risk",
    "falls",
    "drop",
    "miss",
    "downgrade",
    "probe",
    "lawsuit",
    "warning",
    "下跌",
    "风险",
    "下调",
    "处罚",
    "诉讼",
    "预警",
)


@dataclass(frozen=True)
class GoogleNewsRssEvidenceProvider:
    fetcher: Callable[[str], str] | None = None
    max_items_per_narrative: int = 3

    provider_name = GOOGLE_NEWS_RSS_PROVIDER
    provider_version = GOOGLE_NEWS_RSS_VERSION
    source_url = GOOGLE_NEWS_RSS_SOURCE_URL

    def get_news_evidence(
        self,
        narratives: list[dict[str, Any]],
        as_of_date: str,
    ) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        evidence: list[dict[str, Any]] = []
        missing_narrative_ids: list[str] = []
        queried_narrative_ids: list[str] = []
        skipped_item_count = 0
        degradation_events: list[dict[str, str]] = []
        fetcher = self.fetcher or _fetch_text

        for narrative in narratives:
            narrative_id = str(narrative.get("narrative_id") or "")
            if not narrative_id:
                skipped_item_count += 1
                continue
            try:
                feed_url = self._feed_url(narrative)
                rss_text = fetcher(feed_url)
                items = _parse_rss_items(rss_text)
                queried_narrative_ids.append(narrative_id)
            except Exception as exc:
                missing_narrative_ids.append(narrative_id)
                degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider_name": self.provider_name,
                        "reason": f"News RSS fetch failed for {narrative_id}: {exc}",
                    }
                )
                continue

            converted = [
                _news_item_to_evidence(
                    narrative=narrative,
                    item=item,
                    as_of_date=as_of_date,
                    retrieved_at=retrieved_at,
                )
                for item in items[: self.max_items_per_narrative]
            ]
            evidence_items = [item for item in converted if item is not None]
            evidence.extend(evidence_items)
            skipped_item_count += sum(1 for item in converted if item is None)
            if not evidence_items:
                missing_narrative_ids.append(narrative_id)

        payload = {
            "version": NEWS_EVIDENCE_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(evidence, missing_narrative_ids),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "query_scope": _query_scope(
                requested_narrative_ids=[
                    str(item.get("narrative_id") or "") for item in narratives
                ],
                queried_narrative_ids=queried_narrative_ids,
                query_limit=NEWS_EVIDENCE_QUERY_LIMIT,
            ),
            "evidence": sorted(
                evidence,
                key=lambda item: (
                    item["narrative_id"],
                    item["event_date"],
                    item["title"],
                ),
            ),
            "missing_narrative_ids": sorted(set(missing_narrative_ids)),
            "skipped_item_count": skipped_item_count,
            "degradation_events": degradation_events,
        }
        validate_news_evidence_payload(payload)
        return payload

    def _feed_url(self, narrative: dict[str, Any]) -> str:
        terms = _query_terms(narrative)
        query = quote_plus(f"{terms} finance")
        return f"{self.source_url}?q={query}&hl=en-US&gl=US&ceid=US:en"


@dataclass(frozen=True)
class SinaFinanceRollNewsProvider:
    fetcher: Callable[[str], str] | None = None
    max_items_per_narrative: int = 3

    provider_name = SINA_FINANCE_ROLL_PROVIDER
    provider_version = SINA_FINANCE_ROLL_VERSION
    source_url = SINA_FINANCE_ROLL_SOURCE_URL

    def get_news_evidence(
        self,
        narratives: list[dict[str, Any]],
        as_of_date: str,
    ) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        missing_narrative_ids: list[str] = []
        queried_narrative_ids: list[str] = []
        evidence: list[dict[str, Any]] = []
        degradation_events: list[dict[str, str]] = []
        skipped_item_count = 0
        fetcher = self.fetcher or _fetch_text

        try:
            html_text = fetcher(self.source_url)
            articles = _parse_sina_roll_articles(html_text)
        except Exception as exc:
            degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider_name": self.provider_name,
                    "reason": f"Sina Finance roll fetch failed: {exc}",
                }
            )
            articles = []

        for narrative in narratives:
            narrative_id = str(narrative.get("narrative_id") or "")
            if not narrative_id:
                skipped_item_count += 1
                continue
            queried_narrative_ids.append(narrative_id)
            matched = [
                article
                for article in articles
                if _matches_narrative_keywords(
                    headline=article["title"],
                    narrative=narrative,
                )
            ][: self.max_items_per_narrative]
            if not matched:
                missing_narrative_ids.append(narrative_id)
                continue
            converted = [
                _sina_article_to_evidence(
                    narrative=narrative,
                    article=article,
                    as_of_date=as_of_date,
                    retrieved_at=retrieved_at,
                )
                for article in matched
            ]
            evidence_items = [item for item in converted if item is not None]
            evidence.extend(evidence_items)
            skipped_item_count += sum(1 for item in converted if item is None)
            if not evidence_items:
                missing_narrative_ids.append(narrative_id)

        payload = {
            "version": NEWS_EVIDENCE_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(evidence, missing_narrative_ids),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "query_scope": _query_scope(
                requested_narrative_ids=[
                    str(item.get("narrative_id") or "") for item in narratives
                ],
                queried_narrative_ids=queried_narrative_ids,
                query_limit=NEWS_EVIDENCE_QUERY_LIMIT,
            ),
            "evidence": sorted(
                evidence,
                key=lambda item: (
                    item["narrative_id"],
                    item["event_date"],
                    item["title"],
                ),
            ),
            "missing_narrative_ids": sorted(set(missing_narrative_ids)),
            "skipped_item_count": skipped_item_count,
            "degradation_events": degradation_events,
        }
        validate_news_evidence_payload(payload)
        return payload


@dataclass(frozen=True)
class StcnFinanceNewsProvider:
    fetcher: Callable[[str], str] | None = None
    max_items_per_narrative: int = 3

    provider_name = STCN_FINANCE_PROVIDER
    provider_version = STCN_FINANCE_VERSION
    source_url = STCN_FINANCE_SOURCE_URL

    def get_news_evidence(
        self,
        narratives: list[dict[str, Any]],
        as_of_date: str,
    ) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        missing_narrative_ids: list[str] = []
        queried_narrative_ids: list[str] = []
        evidence: list[dict[str, Any]] = []
        degradation_events: list[dict[str, str]] = []
        skipped_item_count = 0
        fetcher = self.fetcher or _fetch_text

        try:
            html_text = fetcher(self.source_url)
            articles = _parse_stcn_articles(html_text)
        except Exception as exc:
            degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider_name": self.provider_name,
                    "reason": f"STCN news fetch failed: {exc}",
                }
            )
            articles = []

        for narrative in narratives:
            narrative_id = str(narrative.get("narrative_id") or "")
            if not narrative_id:
                skipped_item_count += 1
                continue
            queried_narrative_ids.append(narrative_id)
            matched = [
                article
                for article in articles
                if _matches_narrative_keywords(
                    headline=article["title"],
                    narrative=narrative,
                )
            ][: self.max_items_per_narrative]
            if not matched:
                missing_narrative_ids.append(narrative_id)
                continue
            converted = [
                _stcn_article_to_evidence(
                    narrative=narrative,
                    article=article,
                    as_of_date=as_of_date,
                    retrieved_at=retrieved_at,
                )
                for article in matched
            ]
            evidence_items = [item for item in converted if item is not None]
            evidence.extend(evidence_items)
            skipped_item_count += sum(1 for item in converted if item is None)
            if not evidence_items:
                missing_narrative_ids.append(narrative_id)

        payload = {
            "version": NEWS_EVIDENCE_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(evidence, missing_narrative_ids),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "query_scope": _query_scope(
                requested_narrative_ids=[
                    str(item.get("narrative_id") or "") for item in narratives
                ],
                queried_narrative_ids=queried_narrative_ids,
                query_limit=NEWS_EVIDENCE_QUERY_LIMIT,
            ),
            "evidence": sorted(
                evidence,
                key=lambda item: (
                    item["narrative_id"],
                    item["event_date"],
                    item["title"],
                ),
            ),
            "missing_narrative_ids": sorted(set(missing_narrative_ids)),
            "skipped_item_count": skipped_item_count,
            "degradation_events": degradation_events,
        }
        validate_news_evidence_payload(payload)
        return payload


@dataclass(frozen=True)
class MultiSourceNewsEvidenceProvider:
    providers: tuple[Any, ...] | None = None

    provider_name = MULTI_SOURCE_NEWS_PROVIDER
    provider_version = MULTI_SOURCE_NEWS_VERSION
    source_url = "multiple://news"

    def get_news_evidence(
        self,
        narratives: list[dict[str, Any]],
        as_of_date: str,
    ) -> dict[str, Any]:
        providers = self.providers or (
            GoogleNewsRssEvidenceProvider(),
            SinaFinanceRollNewsProvider(),
            StcnFinanceNewsProvider(),
        )
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        degradation_events: list[dict[str, str]] = []
        queried_narrative_ids: set[str] = set()
        evidence_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

        for provider in providers:
            try:
                payload = provider.get_news_evidence(
                    narratives=narratives,
                    as_of_date=as_of_date,
                )
            except Exception as exc:
                degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider_name": str(getattr(provider, "provider_name", "unknown-news-provider")),
                        "reason": f"Multi-source news provider failed: {exc}",
                    }
                )
                continue
            degradation_events.extend(payload.get("degradation_events", []))
            query_scope = payload.get("query_scope") or {}
            queried_narrative_ids.update(
                str(item)
                for item in query_scope.get("queried_narrative_ids", [])
                if item
            )
            for item in payload.get("evidence", []):
                key = (
                    str(item.get("narrative_id") or ""),
                    str(item.get("event_date") or ""),
                    str(item.get("title") or ""),
                )
                existing = evidence_by_key.get(key)
                if existing is None:
                    evidence_by_key[key] = _initialize_corroboration(item)
                    continue
                _merge_corroboration(existing, item)

        evidence = sorted(
            (_finalize_corroboration(item) for item in evidence_by_key.values()),
            key=lambda item: (
                item["narrative_id"],
                item["event_date"],
                item["title"],
            ),
        )
        requested_narrative_ids = [
            str(item.get("narrative_id") or "") for item in narratives if item.get("narrative_id")
        ]
        covered_narrative_ids = {str(item["narrative_id"]) for item in evidence}
        missing_narrative_ids = sorted(
            set(requested_narrative_ids) - covered_narrative_ids
        )
        payload = {
            "version": NEWS_EVIDENCE_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(evidence, missing_narrative_ids),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "query_scope": _query_scope(
                requested_narrative_ids=requested_narrative_ids,
                queried_narrative_ids=sorted(queried_narrative_ids),
                query_limit=NEWS_EVIDENCE_QUERY_LIMIT * len(providers),
            ),
            "evidence": evidence,
            "missing_narrative_ids": missing_narrative_ids,
            "skipped_item_count": 0,
            "degradation_events": degradation_events,
        }
        validate_news_evidence_payload(payload)
        return payload

def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=10) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_rss_items(rss_text: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(rss_text)
    items = []
    for item in root.findall("./channel/item"):
        items.append(
            {
                "title": _node_text(item, "title"),
                "link": _node_text(item, "link"),
                "description": _node_text(item, "description"),
                "pubDate": _node_text(item, "pubDate"),
                "source": _node_text(item, "source"),
            }
        )
    return items


def _parse_sina_roll_articles(html_text: str) -> list[dict[str, str]]:
    parser = _SinaRollParser()
    parser.feed(html_text)
    return parser.articles


def _parse_stcn_articles(html_text: str) -> list[dict[str, str]]:
    parser = _StcnArticleParser()
    parser.feed(html_text)
    return parser.articles


def _node_text(item: ElementTree.Element, tag: str) -> str:
    node = item.find(tag)
    if node is None or node.text is None:
        return ""
    return _clean_text(node.text)


def _news_item_to_evidence(
    narrative: dict[str, Any],
    item: dict[str, str],
    as_of_date: str,
    retrieved_at: str,
) -> dict[str, Any] | None:
    narrative_id = str(narrative.get("narrative_id") or "")
    title = _clean_text(item.get("title") or "")
    source_url = _clean_text(item.get("link") or "")
    if not narrative_id or not title or not source_url:
        return None

    summary_text = _clean_text(item.get("description") or "")
    sentiment = _sentiment(f"{title} {summary_text}")
    event_date = _event_date(item.get("pubDate") or "", as_of_date)
    source_name = _clean_text(item.get("source") or "Google News RSS")
    if not _is_recent_news(event_date=event_date, as_of_date=as_of_date):
        return None
    return {
        "evidence_id": _evidence_id(
            narrative_id=narrative_id,
            title=title,
            event_date=event_date,
            source_url=source_url,
        ),
        "narrative_id": narrative_id,
        "type": "news",
        "source": "google_news_rss",
        "source_url": source_url,
        "title": title,
        "summary": (
            f"{source_name} headline/snippet matched the narrative query. "
            "V1 classified only RSS title/snippet text; article body content was "
            "not parsed."
        ),
        "sentiment": sentiment,
        "confidence": _confidence(sentiment),
        "event_date": event_date,
        "source_provider": GOOGLE_NEWS_RSS_PROVIDER,
        "retrieved_at": retrieved_at,
        "provider_data_quality": "fresh",
        "classification_reason": "keyword heuristic over RSS title/snippet",
    }


def _sina_article_to_evidence(
    narrative: dict[str, Any],
    article: dict[str, str],
    as_of_date: str,
    retrieved_at: str,
 ) -> dict[str, Any] | None:
    narrative_id = str(narrative.get("narrative_id") or "")
    title = _clean_text(article.get("title") or "")
    source_url = _clean_text(article.get("link") or "")
    event_date = _sina_event_date(source_url, as_of_date)
    if not _is_recent_news(event_date=event_date, as_of_date=as_of_date):
        return None
    return {
        "evidence_id": _evidence_id(
            narrative_id=narrative_id,
            title=title,
            event_date=event_date,
            source_url=source_url,
        ),
        "narrative_id": narrative_id,
        "type": "news",
        "source": "sina_finance_roll",
        "source_url": source_url,
        "title": title,
        "summary": (
            "Sina Finance roll headline matched the narrative keywords. "
            "V1 classified only headline text; article body content was not parsed."
        ),
        "sentiment": _sentiment(title),
        "confidence": _confidence(_sentiment(title)),
        "event_date": event_date,
        "source_provider": SINA_FINANCE_ROLL_PROVIDER,
        "retrieved_at": retrieved_at,
        "provider_data_quality": "fresh",
        "classification_reason": "keyword heuristic over Sina Finance headline",
    }


def _stcn_article_to_evidence(
    narrative: dict[str, Any],
    article: dict[str, str],
    as_of_date: str,
    retrieved_at: str,
) -> dict[str, Any] | None:
    narrative_id = str(narrative.get("narrative_id") or "")
    title = _clean_text(article.get("title") or "")
    source_url = _clean_text(article.get("link") or "")
    event_date = _stcn_event_date(source_url, as_of_date)
    if not _is_recent_news(event_date=event_date, as_of_date=as_of_date):
        return None
    sentiment = _sentiment(title)
    return {
        "evidence_id": _evidence_id(
            narrative_id=narrative_id,
            title=title,
            event_date=event_date,
            source_url=source_url,
        ),
        "narrative_id": narrative_id,
        "type": "news",
        "source": "stcn_finance",
        "source_url": source_url,
        "title": title,
        "summary": (
            "STCN headline matched the narrative keywords. "
            "V1 classified only headline text; article body content was not parsed."
        ),
        "sentiment": sentiment,
        "confidence": _confidence(sentiment),
        "event_date": event_date,
        "source_provider": STCN_FINANCE_PROVIDER,
        "retrieved_at": retrieved_at,
        "provider_data_quality": "fresh",
        "classification_reason": "keyword heuristic over STCN headline",
    }


def _query_terms(narrative: dict[str, Any]) -> str:
    name = _clean_text(narrative.get("name") or narrative.get("narrative_id") or "")
    aliases = narrative.get("aliases") if isinstance(narrative.get("aliases"), list) else []
    alias_terms = " ".join(_clean_text(alias) for alias in aliases[:2])
    return f"{name} {alias_terms}".strip()


def _matches_narrative_keywords(headline: str, narrative: dict[str, Any]) -> bool:
    normalized_headline = _clean_text(headline).casefold()
    for keyword in _narrative_keywords(narrative):
        normalized_keyword = keyword.casefold()
        if normalized_keyword and normalized_keyword in normalized_headline:
            return True
    return False


def _narrative_keywords(narrative: dict[str, Any]) -> list[str]:
    fields = [
        narrative.get("name"),
        *(narrative.get("aliases") or []),
        *(narrative.get("related_terms") or []),
    ]
    keywords: list[str] = []
    seen: set[str] = set()
    for value in fields:
        text = _clean_text(value or "")
        if len(text) < 2:
            continue
        lowered = text.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        keywords.append(text)
    return keywords


def _sentiment(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in _NEGATIVE_TERMS):
        return "negative"
    if any(term in lowered for term in _POSITIVE_TERMS):
        return "positive"
    return "mixed"


def _confidence(sentiment: str) -> float:
    base = 0.46 if sentiment == "mixed" else 0.52
    return round(base * DATA_QUALITY_CONFIDENCE["fresh"], 3)


def _event_date(value: str, as_of_date: str) -> str:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        parsed = None
    if parsed is not None:
        return parsed.date().isoformat()
    try:
        return date.fromisoformat(as_of_date).isoformat()
    except ValueError:
        return "1970-01-01"


def _data_quality(
    evidence: list[dict[str, Any]],
    missing_narrative_ids: list[str],
) -> str:
    if not evidence:
        return "unavailable"
    if missing_narrative_ids:
        return "partial"
    return "fresh"


def _is_recent_news(*, event_date: str, as_of_date: str) -> bool:
    try:
        event = date.fromisoformat(event_date)
        anchor = date.fromisoformat(as_of_date)
    except ValueError:
        return True
    age_days = (anchor - event).days
    if age_days < 0:
        return True
    return age_days <= _MAX_NEWS_AGE_DAYS


def _query_scope(
    requested_narrative_ids: list[str],
    queried_narrative_ids: list[str],
    query_limit: int,
) -> dict[str, Any]:
    requested = sorted(narrative_id for narrative_id in set(requested_narrative_ids) if narrative_id)
    queried = sorted(narrative_id for narrative_id in set(queried_narrative_ids) if narrative_id)
    return {
        "requested_narrative_ids": requested,
        "queried_narrative_ids": queried,
        "omitted_narrative_ids": sorted(set(requested) - set(queried)),
        "query_limit": query_limit,
    }


def _evidence_id(
    narrative_id: str,
    title: str,
    event_date: str,
    source_url: str,
) -> str:
    digest = hashlib.sha256(
        f"{narrative_id}|{event_date}|{title}|{source_url}".encode("utf-8")
    ).hexdigest()[:12]
    return f"EV_NEWS_{narrative_id}_{digest.upper()}"


def _clean_text(value: Any) -> str:
    return " ".join(unescape(str(value)).split())


def _sina_event_date(source_url: str, as_of_date: str) -> str:
    match = re.search(r"/(20\d{2})-(\d{2})-(\d{2})/", source_url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return _event_date("", as_of_date)


def _stcn_event_date(source_url: str, as_of_date: str) -> str:
    match = re.search(r"/(20\d{2})[-/](\d{2})[-/](\d{2})/", source_url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return _event_date("", as_of_date)


def _initialize_corroboration(item: dict[str, Any]) -> dict[str, Any]:
    provider_name = str(item.get("source_provider") or item.get("provider_name") or "")
    source_name = str(item.get("source") or "")
    return {
        **item,
        "corroboration_count": 1,
        "corroborating_source_providers": [provider_name] if provider_name else [],
        "corroborating_sources": [source_name] if source_name else [],
    }


def _merge_corroboration(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    providers = list(existing.get("corroborating_source_providers") or [])
    sources = list(existing.get("corroborating_sources") or [])
    provider_name = str(incoming.get("source_provider") or incoming.get("provider_name") or "")
    source_name = str(incoming.get("source") or "")
    if provider_name and provider_name not in providers:
        providers.append(provider_name)
    if source_name and source_name not in sources:
        sources.append(source_name)
    existing["corroborating_source_providers"] = providers
    existing["corroborating_sources"] = sources
    existing["corroboration_count"] = len(providers) if providers else 1


def _finalize_corroboration(item: dict[str, Any]) -> dict[str, Any]:
    providers = list(item.get("corroborating_source_providers") or [])
    count = int(item.get("corroboration_count") or 1)
    if count <= 1 or not providers:
        return item
    provider_list = ", ".join(sorted(providers))
    return {
        **item,
        "summary": (
            f"{item.get('summary') or ''} "
            f"Corroborated by {count} providers: {provider_list}."
        ).strip(),
        "classification_reason": (
            f"{item.get('classification_reason') or 'keyword heuristic'}; "
            f"cross-source corroboration from {count} providers"
        ),
    }


class _SinaRollParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.articles: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        if "sina.com.cn" not in href:
            return
        self._current_href = href
        self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is None:
            return
        self._current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        title = _clean_text(" ".join(self._current_text_parts))
        if title:
            self.articles.append({"title": title, "link": self._current_href})
        self._current_href = None
        self._current_text_parts = []


class _StcnArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.articles: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = _clean_text(dict(attrs).get("href") or "")
        if not _is_stcn_article_link(href):
            return
        self._current_href = href
        self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is None:
            return
        self._current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        title = _clean_text(" ".join(self._current_text_parts))
        if _is_stcn_article_title(title):
            self.articles.append(
                {"title": title, "link": _normalize_stcn_link(self._current_href)}
            )
        self._current_href = None
        self._current_text_parts = []


def _is_stcn_article_link(href: str) -> bool:
    if not href:
        return False
    lowered = href.casefold()
    if any(
        blocked in lowered
        for blocked in (
            "xp.stcn.com",
            "tp.stcn.com",
            "qzs.stcn.com",
            "p5w.net",
            "egsea.com",
            "beian.",
            "javascript:",
            "#",
        )
    ):
        return False
    if lowered.startswith("/article/"):
        return True
    return lowered.startswith("https://www.stcn.com/article/") or lowered.startswith(
        "https://stcn.com/article/"
    )


def _normalize_stcn_link(href: str) -> str:
    if href.startswith("/"):
        return f"https://www.stcn.com{href}"
    return href


def _is_stcn_article_title(title: str) -> bool:
    normalized = _clean_text(title)
    if len(normalized) < 6:
        return False
    if normalized in {"更多", "查看活动"}:
        return False
    return True
