from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import local_env  # noqa: E402
from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.providers.local_gateway import (
    DEFAULT_GATEWAY_BASE_URL_ENV,  # noqa: E402
)
from src.market_data.providers.narrative_source_gateway import (  # noqa: E402
    SOURCE_KIND_PATHS,
    GatewaySourceUnavailableError,
    NarrativeSourceGatewayClient,
)

DEFAULT_SOURCE_KINDS = tuple(SOURCE_KIND_PATHS)
OUTPUT_STEM = "narrative_source_gateway_probe"
DEFAULT_PROBE_REQUESTS = {
    "official_filings": {
        "symbols": ["AAPL"],
        "query": "AI infrastructure",
    },
    "official_disclosures": {
        "symbols": ["000001.SZ"],
        "query": "股东会",
    },
    "news_context": {
        "symbols": [],
        "query": "半导体 A股",
    },
    "social_heat": {
        "symbols": ["AAPL"],
        "query": "Apple",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe FNI's provider-neutral narrative source gateway consumer."
    )
    parser.add_argument("--base-url")
    parser.add_argument("--source-kind", action="append", choices=DEFAULT_SOURCE_KINDS)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--fixture-json", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "narrative_source_gateway_probe" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_kinds = tuple(args.source_kind or DEFAULT_SOURCE_KINDS)
    base_url = args.base_url or local_env.get_config_value(DEFAULT_GATEWAY_BASE_URL_ENV)
    report = run_probe(
        base_url=base_url,
        source_kinds=source_kinds,
        symbols=args.symbol,
        query=args.query,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
        fixture_json=args.fixture_json,
    )
    write_outputs(args.output_dir, report)
    return 0 if report["summary"]["failed_source_kinds"] == 0 else 1


def run_probe(
    *,
    base_url: str | None,
    source_kinds: tuple[str, ...],
    symbols: list[str],
    query: str,
    limit: int,
    timeout_seconds: float,
    fixture_json: Path | None = None,
) -> dict[str, Any]:
    fixture_payloads = _load_fixture_payloads(fixture_json)
    if not base_url:
        results = [
            _failure_result(
                source_kind=source_kind,
                reason=f"{DEFAULT_GATEWAY_BASE_URL_ENV} is not configured",
            )
            for source_kind in source_kinds
        ]
        return _report(base_url="", source_results=results, fixture_mode=bool(fixture_json))
    client = NarrativeSourceGatewayClient(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        fetcher=_fixture_fetcher(fixture_payloads) if fixture_payloads is not None else None,
    )
    results = []
    for source_kind in source_kinds:
        default_request = DEFAULT_PROBE_REQUESTS[source_kind]
        request_symbols = symbols or list(default_request["symbols"])
        request_query = query or str(default_request["query"])
        try:
            result = client.fetch_source_events(
                source_kind=source_kind,
                symbols=request_symbols or None,
                query=request_query or None,
                limit=limit,
            )
            results.append({**result, "failure_reason": ""})
        except (GatewaySourceUnavailableError, ValueError) as exc:
            results.append(_failure_result(source_kind=source_kind, reason=str(exc)))
    return _report(base_url=base_url, source_results=results, fixture_mode=bool(fixture_json))


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{OUTPUT_STEM}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{OUTPUT_STEM}.html").write_text(
        render_html(report),
        encoding="utf-8",
    )


def render_html(report: dict[str, Any]) -> str:
    rows = "\n".join(_html_rows(report["source_results"]))
    summary = report["summary"]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>叙事来源 Gateway 消费探针</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; }}
    .meta {{ color: #4b5563; line-height: 1.6; }}
    .notice {{ margin: 18px 0; padding: 12px 14px; border-left: 4px solid #b45309; background: #fff7ed; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 18px; font-size: 13px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>叙事来源 Gateway 消费探针</h1>
  <div class="meta">
    <div>生成时间：<code>{html.escape(report["generated_at"])}</code></div>
    <div>Gateway：<code>{html.escape(report["base_url"] or "未配置")}</code></div>
    <div>完成来源：<code>{summary["completed_source_kinds"]}</code> / <code>{summary["total_source_kinds"]}</code>，失败来源：<code>{summary["failed_source_kinds"]}</code></div>
  </div>
  <div class="notice">本报告只展示 Gateway 返回的候选来源标签和质量口径，不能把未支持的候选信号表述为确定事实。</div>
  <table>
    <thead>
      <tr>
        <th>来源类型</th>
        <th>状态</th>
        <th>标题</th>
        <th>trust_tier</th>
        <th>source_quality</th>
        <th>license_scope</th>
        <th>retention_policy</th>
        <th>metadata_only</th>
        <th>degradation_events</th>
        <th>失败原因</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def _html_rows(source_results: list[dict[str, Any]]) -> list[str]:
    rendered = []
    for result in source_results:
        rows = result.get("rows") or [{}]
        for row in rows:
            degradation = row.get("degradation_events") or result.get("degradation_events") or []
            rendered.append(
                "      <tr>"
                f"<td><code>{html.escape(str(result.get('source_kind') or ''))}</code></td>"
                f"<td>{html.escape(str(result.get('status') or ''))}</td>"
                f"<td>{html.escape(str(row.get('title') or ''))}</td>"
                f"<td><code>{html.escape(str(row.get('trust_tier') or ''))}</code></td>"
                f"<td><code>{html.escape(str(row.get('source_quality') or ''))}</code></td>"
                f"<td>{html.escape(str(row.get('license_scope') or ''))}</td>"
                f"<td><code>{html.escape(str(row.get('retention_policy') or ''))}</code></td>"
                f"<td><code>{html.escape(str(row.get('metadata_only') if 'metadata_only' in row else ''))}</code></td>"
                f"<td>{html.escape(json.dumps(degradation, ensure_ascii=False))}</td>"
                f"<td>{html.escape(str(result.get('failure_reason') or ''))}</td>"
                "</tr>"
            )
    return rendered


def _report(
    *,
    base_url: str,
    source_results: list[dict[str, Any]],
    fixture_mode: bool,
) -> dict[str, Any]:
    failed = [result for result in source_results if result.get("status") == "failed"]
    completed = [
        result for result in source_results if result.get("status") == "completed"
    ]
    return {
        "version": "narrative-source-gateway-probe-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "base_url": base_url,
        "fixture_mode": fixture_mode,
        "summary": {
            "total_source_kinds": len(source_results),
            "completed_source_kinds": len(completed),
            "failed_source_kinds": len(failed),
            "total_rows": sum(int(result.get("row_count") or 0) for result in source_results),
        },
        "source_results": source_results,
        "disclosure": {
            "trust_statement": (
                "FNI reports only gateway-provided trust/source/license labels; "
                "candidate signals are not promoted to trusted facts automatically."
            ),
            "direct_external_source_calls": False,
        },
    }


def _failure_result(*, source_kind: str, reason: str) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "status": "failed",
        "row_count": 0,
        "rows": [],
        "meta": {},
        "degradation_events": [{"code": "gateway_unavailable", "message": reason}],
        "failure_reason": reason,
    }


def _load_fixture_payloads(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--fixture-json must contain an object keyed by source kind")
    return payload


def _fixture_fetcher(payloads: dict[str, Any]):
    def fetcher(
        method: str,
        url: str,
        json_body: dict[str, Any] | None,
        timeout_seconds: float,
    ) -> tuple[int, dict[str, Any]]:
        del method, json_body, timeout_seconds
        source_kind = _source_kind_for_url(url)
        payload = payloads.get(source_kind)
        if not isinstance(payload, dict):
            return 404, {
                "error": {
                    "code": "FIXTURE_SOURCE_KIND_MISSING",
                    "message": f"fixture missing {source_kind}",
                }
            }
        return 200, payload

    return fetcher


def _source_kind_for_url(url: str) -> str:
    for source_kind, path in SOURCE_KIND_PATHS.items():
        if url.endswith(path):
            return source_kind
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
