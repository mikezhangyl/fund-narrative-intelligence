from __future__ import annotations

import json

from scripts import run_public_news_context_smoke
from src.scanners.public_news_context import (
    build_public_news_context_report,
    render_public_news_context_html,
)


def test_public_news_context_normalizes_google_rss_as_context_only():
    report = build_public_news_context_report(
        google_rss_xml=_google_rss(),
        sina_html="",
        fetched_at="2026-06-01T00:00:00+00:00",
        query="半导体 A股",
    )

    assert report["version"] == "public-news-context-v1"
    assert report["summary"]["returned_item_count"] == 2
    assert report["summary"]["skipped_noise_count"] == 0
    first = report["items"][0]
    assert first["provider"] == "google-news-rss"
    assert first["context_trust_tier"] == "context_only"
    assert first["source_quality_label"] == "public_rss_context"
    assert first["parser_health"] == "parsed"
    assert first["source_domain"] == "example.com"
    assert first["published_at"] == "2026-05-31T08:00:00+00:00"
    assert "trusted_fact" not in json.dumps(report, ensure_ascii=False)


def test_public_news_context_filters_sina_navigation_noise():
    report = build_public_news_context_report(
        google_rss_xml="",
        sina_html=_sina_html_with_noise(),
        fetched_at="2026-06-01T00:00:00+00:00",
        query="半导体 A股",
    )

    assert report["summary"]["returned_item_count"] == 1
    assert report["summary"]["skipped_noise_count"] == 3
    item = report["items"][0]
    assert item["provider"] == "sina-finance-roll"
    assert item["title"] == "半导体设备订单升温，A股产业链受关注"
    assert item["context_trust_tier"] == "context_only"
    assert item["source_quality_label"] == "public_roll_context"
    assert item["source_domain"] == "finance.sina.com.cn"


def test_public_news_context_html_is_chinese_and_discloses_quality_labels():
    html = render_public_news_context_html(
        build_public_news_context_report(
            google_rss_xml=_google_rss(),
            sina_html=_sina_html_with_noise(),
            fetched_at="2026-06-01T00:00:00+00:00",
            query="半导体 A股",
        )
    )

    assert "<h1>公共新闻上下文清洗报告</h1>" in html
    assert "context_only" in html
    assert "public_rss_context" in html
    assert "public_roll_context" in html
    assert "不能直接生成 trusted narrative fact" in html


def test_public_news_context_smoke_cli_writes_json_and_html(tmp_path):
    google_path = tmp_path / "google.xml"
    sina_path = tmp_path / "sina.html"
    output_dir = tmp_path / "out"
    google_path.write_text(_google_rss(), encoding="utf-8")
    sina_path.write_text(_sina_html_with_noise(), encoding="utf-8")

    exit_code = run_public_news_context_smoke.main(
        [
            "--query",
            "半导体 A股",
            "--google-rss-xml",
            str(google_path),
            "--sina-html",
            str(sina_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads((output_dir / "public_news_context.json").read_text())
    html = (output_dir / "public_news_context.html").read_text()

    assert payload["summary"]["returned_item_count"] == 3
    assert payload["summary"]["skipped_noise_count"] == 3
    assert {item["context_trust_tier"] for item in payload["items"]} == {"context_only"}
    assert "<h1>公共新闻上下文清洗报告</h1>" in html


def _google_rss() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>半导体 A股设备订单升温 - Example</title>
      <link>https://example.com/news/a</link>
      <pubDate>Sun, 31 May 2026 08:00:00 GMT</pubDate>
      <source>Example News</source>
    </item>
    <item>
      <title>晶圆厂资本开支预期改善 - Example</title>
      <link>https://example.com/news/b</link>
      <pubDate>Sun, 31 May 2026 09:30:00 GMT</pubDate>
      <source>Example News</source>
    </item>
  </channel>
</rss>
"""


def _sina_html_with_noise() -> str:
    return """
<html>
  <body>
    <a href="https://finance.sina.com.cn/">新浪财经首页</a>
    <a href="https://finance.sina.com.cn/roll/">滚动新闻</a>
    <a href="https://finance.sina.com.cn/client/">客户端下载</a>
    <a href="https://finance.sina.com.cn/stock/2026-05-31/doc-semiconductor.shtml">
      半导体设备订单升温，A股产业链受关注
    </a>
  </body>
</html>
"""
