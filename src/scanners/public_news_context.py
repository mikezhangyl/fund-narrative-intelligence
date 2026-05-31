from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import escape
from typing import Any
from urllib.parse import urlparse

from src.providers.news import (
    GOOGLE_NEWS_RSS_PROVIDER,
    SINA_FINANCE_ROLL_PROVIDER,
    _parse_rss_items,
    _parse_sina_roll_articles,
)

PUBLIC_NEWS_CONTEXT_VERSION = "public-news-context-v1"

NOISE_TITLES = (
    "首页",
    "新浪财经首页",
    "滚动新闻",
    "财经首页",
    "股票首页",
    "客户端下载",
    "客户端",
    "视频",
    "直播",
    "更多",
)


def build_public_news_context_report(
    *,
    google_rss_xml: str,
    sina_html: str,
    fetched_at: str | None = None,
    query: str,
) -> dict[str, Any]:
    retrieved_at = fetched_at or _utc_now()
    google_items = _google_context_items(
        google_rss_xml,
        fetched_at=retrieved_at,
        query=query,
    )
    sina_items, sina_noise_count = _sina_context_items(
        sina_html,
        fetched_at=retrieved_at,
        query=query,
    )
    items = [*google_items, *sina_items]
    return {
        "version": PUBLIC_NEWS_CONTEXT_VERSION,
        "query": query,
        "fetched_at": retrieved_at,
        "summary": {
            "returned_item_count": len(items),
            "skipped_noise_count": sina_noise_count,
            "google_item_count": len(google_items),
            "sina_item_count": len(sina_items),
            "context_trust_tier": "context_only",
        },
        "items": items,
        "policy": {
            "public_news_trust_tier": "context_only",
            "direct_fact_allowed": False,
            "promotion_effect": "none",
        },
    }


def render_public_news_context_html(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>公共新闻上下文清洗报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>公共新闻上下文清洗报告</h1>",
            '<section class="summary">',
            "<p>Google News RSS 与 Sina Finance roll 只作为 context_only 公共新闻上下文；不能直接生成 trusted narrative fact。</p>",
            _html_kv("查询", report.get("query", "")),
            _html_kv("返回条目", summary.get("returned_item_count", 0)),
            _html_kv("跳过噪声", summary.get("skipped_noise_count", 0)),
            _html_kv("信任层级", summary.get("context_trust_tier", "")),
            "</section>",
            _items_table(_list(report.get("items"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _google_context_items(
    rss_xml: str,
    *,
    fetched_at: str,
    query: str,
) -> list[dict[str, Any]]:
    if not rss_xml.strip():
        return []
    rows = _parse_rss_items(rss_xml)
    return [
        _context_item(
            provider=GOOGLE_NEWS_RSS_PROVIDER,
            title=row.get("title", ""),
            link=row.get("link", ""),
            published_at=_published_at(row.get("pubDate", "")),
            source_name=row.get("source", ""),
            fetched_at=fetched_at,
            query=query,
            source_quality_label="public_rss_context",
            parser_health="parsed",
        )
        for row in rows
        if row.get("title") and row.get("link")
    ]


def _sina_context_items(
    html: str,
    *,
    fetched_at: str,
    query: str,
) -> tuple[list[dict[str, Any]], int]:
    if not html.strip():
        return [], 0
    rows = _parse_sina_roll_articles(html)
    items = []
    skipped = 0
    for row in rows:
        title = str(row.get("title") or "")
        link = str(row.get("link") or "")
        if _is_sina_noise(title=title, link=link):
            skipped += 1
            continue
        items.append(
            _context_item(
                provider=SINA_FINANCE_ROLL_PROVIDER,
                title=title,
                link=link,
                published_at="",
                source_name="Sina Finance",
                fetched_at=fetched_at,
                query=query,
                source_quality_label="public_roll_context",
                parser_health="parsed_with_noise_filter",
            )
        )
    return items, skipped


def _context_item(
    *,
    provider: str,
    title: str,
    link: str,
    published_at: str,
    source_name: str,
    fetched_at: str,
    query: str,
    source_quality_label: str,
    parser_health: str,
) -> dict[str, Any]:
    return {
        "item_id": _stable_id("PNEWS", [provider, link, title, published_at]),
        "provider": provider,
        "title": _clean_text(title),
        "link": _clean_text(link),
        "published_at": published_at,
        "source_domain": _source_domain(link),
        "source_name": _clean_text(source_name),
        "fetched_at": fetched_at,
        "query": query,
        "source_quality_label": source_quality_label,
        "parser_health": parser_health,
        "context_trust_tier": "context_only",
        "promotion_effect": "none",
        "direct_fact_allowed": False,
    }


def _is_sina_noise(*, title: str, link: str) -> bool:
    clean_title = _clean_text(title)
    clean_link = _clean_text(link)
    if not clean_title or not clean_link:
        return True
    if clean_title in NOISE_TITLES or len(clean_title) < 8:
        return True
    path = urlparse(clean_link).path
    if path in {"", "/", "/roll/", "/client/"}:
        return True
    return not (
        clean_link.endswith(".shtml")
        or "/doc-" in clean_link
        or re.search(r"/20\d{2}-\d{2}-\d{2}/", clean_link) is not None
    )


def _published_at(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat()


def _source_domain(link: str) -> str:
    parsed = urlparse(link)
    return parsed.netloc.lower()


def _items_table(items: list[Any]) -> str:
    rows = [_mapping(item) for item in items]
    if not rows:
        return "<section><h2>新闻上下文</h2><p>没有可展示条目。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("Provider", "标题", "发布时间", "域名", "质量标签", "Parser", "Trust")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('provider'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(row.get('published_at'))}</td>"
        f"<td>{_html_text(row.get('source_domain'))}</td>"
        f"<td>{_html_text(row.get('source_quality_label'))}</td>"
        f"<td>{_html_text(row.get('parser_health'))}</td>"
        f"<td>{_html_text(row.get('context_trust_tier'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>新闻上下文</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _stable_id(prefix: str, values: list[Any]) -> str:
    import hashlib

    digest = hashlib.sha1(
        "|".join(str(value or "") for value in values).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16].upper()}"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
