from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.providers.news import (  # noqa: E402
    GOOGLE_NEWS_RSS_SOURCE_URL,
    SINA_FINANCE_ROLL_SOURCE_URL,
)
from src.scanners.public_news_context import (  # noqa: E402
    build_public_news_context_report,
    render_public_news_context_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build public news context-only rows from Google News RSS and Sina Finance roll."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--google-rss-xml", type=Path, default=None)
    parser.add_argument("--sina-html", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "public_news_context",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    google_rss_xml = (
        args.google_rss_xml.read_text(encoding="utf-8")
        if args.google_rss_xml
        else _fetch_text(_google_rss_url(args.query))
    )
    sina_html = (
        args.sina_html.read_text(encoding="utf-8")
        if args.sina_html
        else _fetch_text(SINA_FINANCE_ROLL_SOURCE_URL)
    )
    report = build_public_news_context_report(
        google_rss_xml=google_rss_xml,
        sina_html=sina_html,
        query=args.query,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "public_news_context.json"
    html_path = args.output_dir / "public_news_context.html"
    _write_json(json_path, report)
    html_path.write_text(render_public_news_context_html(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "returned_item_count": report.get("summary", {}).get("returned_item_count", 0),
                "skipped_noise_count": report.get("summary", {}).get("skipped_noise_count", 0),
                "json_path": str(json_path),
                "html_path": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _google_rss_url(query: str) -> str:
    encoded = quote_plus(query)
    return f"{GOOGLE_NEWS_RSS_SOURCE_URL}?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
