from __future__ import annotations

# ruff: noqa: E402
import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import local_env  # noqa: E402
from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.providers.local_gateway import (  # noqa: E402
    DEFAULT_GATEWAY_BASE_URL_ENV,
)
from src.market_data.providers.narrative_source_gateway import (  # noqa: E402
    SOURCE_KIND_PATHS,
    GatewaySourceUnavailableError,
    NarrativeSourceGatewayClient,
    normalize_gateway_source_event,
)
from src.modules.narrative_review.live_review_page import (  # noqa: E402
    build_live_narrative_review_page,
    render_live_narrative_review_page_html,
)

DEFAULT_TOPICS = ("AI infrastructure", "solar/storage")
DEFAULT_SOURCE_KINDS = tuple(SOURCE_KIND_PATHS)
OUTPUT_STEM = "live_narrative_review_page"
DEFAULT_TOPIC_SOURCE_REQUESTS = {
    "AI infrastructure": {
        "official_filings": {"symbols": ["NVDA"], "query": ""},
        "official_disclosures": {"symbols": [], "query": "AI"},
        "official_sources": {"symbols": [], "query": "AI"},
        "news_context": {"symbols": [], "query": "AI"},
        "open_news_index": {"symbols": [], "query": "AI"},
        "industry_media": {"symbols": [], "query": "AI"},
        "social_heat": {"symbols": ["NVDA"], "query": ""},
    },
    "solar/storage": {
        "official_filings": {"symbols": ["TSLA"], "query": ""},
        "official_disclosures": {"symbols": ["300750.SZ"], "query": ""},
        "official_sources": {"symbols": [], "query": "climate"},
        "news_context": {"symbols": [], "query": "solar"},
        "open_news_index": {"symbols": [], "query": "solar"},
        "industry_media": {"symbols": [], "query": "solar"},
        "social_heat": {"symbols": ["TSLA"], "query": ""},
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a visible Chinese live narrative review page from Gateway source events."
    )
    parser.add_argument("--base-url")
    parser.add_argument("--topic", action="append")
    parser.add_argument("--source-kind", action="append", choices=DEFAULT_SOURCE_KINDS)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--fixture-json", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "live_narrative_review_page" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    topics = tuple(args.topic or DEFAULT_TOPICS)
    source_kinds = tuple(args.source_kind or DEFAULT_SOURCE_KINDS)
    base_url = args.base_url or local_env.get_config_value(DEFAULT_GATEWAY_BASE_URL_ENV) or ""
    fixture_payloads = _load_fixture_payloads(args.fixture_json)
    topic_results = _fetch_topic_results(
        base_url=base_url or "http://fixture-gateway.local",
        topics=topics,
        source_kinds=source_kinds,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
        fixture_payloads=fixture_payloads,
    )
    page = build_live_narrative_review_page(
        topic_results=topic_results,
        base_url=base_url,
        fixture_mode=fixture_payloads is not None,
    )
    write_outputs(args.output_dir, page)
    print(
        json.dumps(
            {
                "status": "ok",
                "candidate_count": page["summary"]["candidate_count"],
                "source_event_count": page["summary"]["source_event_count"],
                "json": str(args.output_dir / f"{OUTPUT_STEM}.json"),
                "html": str(args.output_dir / f"{OUTPUT_STEM}.html"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def write_outputs(output_dir: Path, page: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{OUTPUT_STEM}.json").write_text(
        json.dumps(page, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{OUTPUT_STEM}.html").write_text(
        render_live_narrative_review_page_html(page),
        encoding="utf-8",
    )


def _fetch_topic_results(
    *,
    base_url: str,
    topics: tuple[str, ...],
    source_kinds: tuple[str, ...],
    limit: int,
    timeout_seconds: float,
    fixture_payloads: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not base_url and fixture_payloads is None:
        return [
            {
                "topic_name": topic,
                "query": topic,
                "source_results": [
                    _failure_result(
                        source_kind=source_kind,
                        status="blocked",
                        reason=f"{DEFAULT_GATEWAY_BASE_URL_ENV} is not configured",
                    )
                    for source_kind in source_kinds
                ],
            }
            for topic in topics
        ]
    client = NarrativeSourceGatewayClient(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
    return [
        {
            "topic_name": topic,
            "query": topic,
            "source_results": [
                (
                    _fixture_source_result(
                        fixture_payloads=fixture_payloads,
                        topic=topic,
                        source_kind=source_kind,
                    )
                    if fixture_payloads is not None
                    else _fetch_source_kind(
                        client=client,
                        topic=topic,
                        source_kind=source_kind,
                        limit=limit,
                    )
                )
                for source_kind in source_kinds
            ],
        }
        for topic in topics
    ]


def _fetch_source_kind(
    *,
    client: NarrativeSourceGatewayClient,
    topic: str,
    source_kind: str,
    limit: int,
) -> dict[str, Any]:
    try:
        request = _source_request(topic=topic, source_kind=source_kind)
        return {
            **client.fetch_source_events(
                source_kind=source_kind,
                symbols=request["symbols"] or None,
                query=request["query"] or None,
                limit=limit,
            ),
            "request": {
                "topic": topic,
                "symbols": request["symbols"],
                "query": request["query"],
            },
            "failure_reason": "",
        }
    except ValueError as exc:
        return _failure_result(
            source_kind=source_kind,
            status="schema_mismatch",
            reason=str(exc),
        )
    except GatewaySourceUnavailableError as exc:
        return _failure_result(
            source_kind=source_kind,
            status="blocked",
            reason=str(exc),
        )


def _source_request(*, topic: str, source_kind: str) -> dict[str, Any]:
    topic_requests = DEFAULT_TOPIC_SOURCE_REQUESTS.get(topic, {})
    source_request = topic_requests.get(source_kind)
    if isinstance(source_request, dict):
        return {
            "symbols": [str(symbol) for symbol in source_request.get("symbols", [])],
            "query": str(source_request.get("query") or ""),
        }
    return {"symbols": [], "query": topic}


def _failure_result(*, source_kind: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "status": status,
        "row_count": 0,
        "rows": [],
        "meta": {},
        "degradation_events": [{"code": status.upper(), "message": reason}],
        "failure_reason": reason,
    }


def _load_fixture_payloads(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture_source_result(
    *,
    fixture_payloads: dict[str, Any] | None,
    topic: str,
    source_kind: str,
) -> dict[str, Any]:
    topic_payload = _topic_fixture(fixture_payloads or {}, topic)
    payload = _mapping(topic_payload).get(source_kind)
    if not isinstance(payload, dict):
        return {
            "source_kind": source_kind,
            "status": "missing",
            "row_count": 0,
            "rows": [],
            "meta": {"status": "missing"},
            "degradation_events": [
                {
                    "code": "NO_ROWS",
                    "message": f"No fixture rows for {topic} / {source_kind}.",
                }
            ],
            "failure_reason": "",
        }
    meta = _mapping(payload.get("meta"))
    rows = _list(_mapping(payload.get("data")).get("rows"))
    try:
        normalized_rows = [
            {**normalize_gateway_source_event(row), "source_kind": source_kind}
            for row in rows
            if isinstance(row, dict)
        ]
    except ValueError as exc:
        return _failure_result(
            source_kind=source_kind,
            status="schema_mismatch",
            reason=str(exc),
        )
    status = "degraded" if str(meta.get("status") or "").casefold() == "degraded" else "completed"
    if not normalized_rows and status != "degraded":
        status = "missing"
    return {
        "source_kind": source_kind,
        "status": status,
        "row_count": len(normalized_rows),
        "rows": normalized_rows,
        "meta": meta,
        "degradation_events": _list(meta.get("degradation_events")),
        "failure_reason": "",
    }


def _topic_fixture(payloads: dict[str, Any], topic: str) -> dict[str, Any]:
    if topic in payloads and isinstance(payloads[topic], dict):
        return payloads[topic]
    normalized = _normalize_topic(topic)
    for key, value in payloads.items():
        if _normalize_topic(str(key)) == normalized and isinstance(value, dict):
            return value
    return {}


def _normalize_topic(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
