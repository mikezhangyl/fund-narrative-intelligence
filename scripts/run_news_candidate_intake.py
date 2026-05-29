from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REVIEWED_REGISTRY_PATH,
    FIXTURE_DIR,
)
from src.market_data.source_layer import ConsolidatedMarketDataSource  # noqa: E402
from src.scanners.news_candidate_intake import (  # noqa: E402
    build_news_candidate_intake_report,
    render_news_candidate_intake_html,
)

DEFAULT_NEWS_BRIEFS_PATH = FIXTURE_DIR / "news_briefs_for_candidate_intake.v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run structured news briefs through candidate narrative intake."
    )
    parser.add_argument("--news-briefs-path", type=Path, default=DEFAULT_NEWS_BRIEFS_PATH)
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REVIEWED_REGISTRY_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR / "news_candidate_intake")
    parser.add_argument("--provider", default="gateway_news_briefs")
    parser.add_argument("--source-provider", default="tushare")
    parser.add_argument("--src", default="sina")
    parser.add_argument("--start-datetime")
    parser.add_argument("--end-datetime")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch news briefs from the configured gateway instead of reading --news-briefs-path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.live and (not args.start_datetime or not args.end_datetime):
        raise SystemExit("--live requires --start-datetime and --end-datetime")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")

    news_payload = _live_news_payload(args) if args.live else _read_json(args.news_briefs_path)
    registry_payload = _read_json(args.registry_path)
    report = build_news_candidate_intake_report(
        news_payload=news_payload,
        registry_payload=registry_payload,
        provider=args.provider,
        source_provider=args.source_provider,
        src=args.src,
    )
    _write_outputs(output_dir=args.output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "news_candidate_intake_report.json"),
                "html": str(args.output_dir / "news_candidate_intake_report.html"),
                "status": report["status"],
                "event_count": report["summary"]["event_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _live_news_payload(args: argparse.Namespace) -> dict[str, Any]:
    rows = ConsolidatedMarketDataSource().fetch_news_briefs(
        source_provider=args.source_provider,
        src=args.src,
        start_datetime=args.start_datetime,
        end_datetime=args.end_datetime,
        limit=args.limit,
    )
    return {"version": "live-news-briefs-v1", "rows": rows}


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "news_candidate_intake_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "news_candidate_intake_report.html").write_text(
        render_news_candidate_intake_html(report),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
