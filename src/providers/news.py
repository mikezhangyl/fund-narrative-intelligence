from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any, Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from src.config import DATA_QUALITY_CONFIDENCE
from src.validation import validate_news_evidence_payload

GOOGLE_NEWS_RSS_PROVIDER = "google-news-rss"
GOOGLE_NEWS_RSS_VERSION = "google-news-rss-v1"
GOOGLE_NEWS_RSS_SOURCE_URL = "https://news.google.com/rss/search"
NEWS_EVIDENCE_VERSION = "news-evidence-v1"
NEWS_EVIDENCE_QUERY_LIMIT = 4

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


def _query_terms(narrative: dict[str, Any]) -> str:
    name = _clean_text(narrative.get("name") or narrative.get("narrative_id") or "")
    aliases = narrative.get("aliases") if isinstance(narrative.get("aliases"), list) else []
    alias_terms = " ".join(_clean_text(alias) for alias in aliases[:2])
    return f"{name} {alias_terms}".strip()


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
