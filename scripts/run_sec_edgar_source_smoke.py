from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.providers.sec_edgar import (  # noqa: E402
    DEFAULT_SEC_USER_AGENT,
    SecEdgarSubmissionsProvider,
    render_sec_edgar_smoke_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch or normalize SEC EDGAR submissions into source-event rows."
    )
    parser.add_argument("--cik", required=True)
    parser.add_argument("--ticker", default="")
    parser.add_argument("--company-name", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--input-json", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "sec_edgar_source_smoke",
    )
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("SEC_EDGAR_USER_AGENT", DEFAULT_SEC_USER_AGENT),
        help="SEC requests require a descriptive User-Agent.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    provider = SecEdgarSubmissionsProvider(
        fetcher=_fixture_fetcher(args.input_json) if args.input_json else None,
        user_agent=args.user_agent,
    )
    payload = provider.get_submissions(
        cik=args.cik,
        ticker=args.ticker,
        company_name=args.company_name,
        limit=args.limit,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "sec_edgar_source_smoke.json"
    html_path = args.output_dir / "sec_edgar_source_smoke.html"
    _write_json(json_path, payload)
    html_path.write_text(render_sec_edgar_smoke_html(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "data_quality": payload.get("data_quality"),
                "event_count": payload.get("summary", {}).get("event_count", 0),
                "json_path": str(json_path),
                "html_path": str(html_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _fixture_fetcher(input_json: Path):
    def fetcher(_url: str, _headers: dict[str, str]) -> dict[str, Any]:
        return json.loads(input_json.read_text(encoding="utf-8"))

    return fetcher


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
