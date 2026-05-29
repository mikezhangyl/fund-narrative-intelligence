from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402

STATUS_TAXONOMY = [
    "passed",
    "degraded",
    "blocked",
    "not_configured",
    "product_gap",
    "system_failure",
]

FetchJson = Callable[
    ...,
    tuple[int, dict[str, Any]],
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a live validation dashboard for gateway and Narrative Service."
    )
    parser.add_argument("--gateway-url", default=os.environ.get("MARKET_DATA_GATEWAY_URL", ""))
    parser.add_argument("--service-url", default=os.environ.get("NARRATIVE_SERVICE_URL", ""))
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--fund-code", default="161725")
    parser.add_argument("--stock-symbol", default="600519.SH")
    parser.add_argument("--trade-date", default="20260522")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or _default_output_dir()
    report = build_dashboard(
        gateway_url=args.gateway_url,
        service_url=args.service_url,
        generated_at=_now(),
        timeout_seconds=args.timeout_seconds,
        fund_code=args.fund_code,
        stock_symbol=args.stock_symbol,
        trade_date=args.trade_date,
    )
    outputs = write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                **outputs,
                "status": report["summary"]["overall_status"],
                "system_failure_count": report["summary"]["system_failure_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["summary"]["system_failure_count"] == 0 else 1


def build_dashboard(
    *,
    gateway_url: str,
    service_url: str,
    generated_at: str,
    timeout_seconds: float,
    fund_code: str = "161725",
    stock_symbol: str = "600519.SH",
    trade_date: str = "20260522",
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    fetcher = fetch_json or _fetch_json
    rows = [
        _deterministic_contract_row(),
        _gateway_configuration_row(gateway_url=gateway_url),
        _probe_row(
            group="fund_holdings",
            capability="gateway_fund_holdings",
            mode="live_provider",
            base_url=gateway_url,
            method="GET",
            path="/api/v1/market-data/funds/holdings",
            query={"fund_code": fund_code, "limit": 10},
            timeout_seconds=timeout_seconds,
            fetch_json=fetcher,
        ),
        _probe_row(
            group="daily_bars",
            capability="gateway_daily_bars",
            mode="live_provider",
            base_url=gateway_url,
            method="POST",
            path="/api/v1/market-data/tushare/daily",
            payload={
                "symbols": [stock_symbol],
                "start_date": trade_date,
                "end_date": trade_date,
                "include_turnover": True,
            },
            timeout_seconds=timeout_seconds,
            fetch_json=fetcher,
        ),
        _combined_gateway_row(
            base_url=gateway_url,
            timeout_seconds=timeout_seconds,
            trade_date=trade_date,
            fetch_json=fetcher,
        ),
        _probe_row(
            group="narrative_service",
            capability="narrative_service_health",
            mode="live_provider",
            base_url=service_url,
            method="GET",
            path="/api/health",
            timeout_seconds=timeout_seconds,
            fetch_json=fetcher,
        ),
        _probe_row(
            group="narrative_service",
            capability="narrative_service_ops",
            mode="live_provider",
            base_url=service_url,
            method="GET",
            path="/api/v1/narratives/ops/summary",
            timeout_seconds=timeout_seconds,
            fetch_json=fetcher,
        ),
        _probe_row(
            group="review_workspace",
            capability="narrative_review_workspace",
            mode="live_provider",
            base_url=service_url,
            method="GET",
            path="/api/v1/narratives/review-queue",
            timeout_seconds=timeout_seconds,
            fetch_json=fetcher,
        ),
    ]
    return {
        "version": "live-validation-dashboard-v1",
        "generated_at": generated_at,
        "taxonomy": {
            "statuses": STATUS_TAXONOMY,
            "aliases": {"not_configured": ["missing_config", "missing_url"]},
            "rules": {
                "passed": "Configured probe returned usable payload data.",
                "degraded": "Probe returned data with warnings or degraded status.",
                "blocked": "Probe reached a configured service but authorization or request semantics blocked it.",
                "not_configured": "Required local gateway or Narrative Service URL is absent.",
                "product_gap": "Service is reachable but returned no business data for the requested probe.",
                "system_failure": "Runtime, network, timeout, or server failure prevented validation.",
            },
        },
        "inputs": {
            "gateway_url_configured": bool(gateway_url.strip()),
            "service_url_configured": bool(service_url.strip()),
            "timeout_seconds": timeout_seconds,
            "fund_code": fund_code,
            "stock_symbol": stock_symbol,
            "trade_date": trade_date,
            "external_provider_policy": "FNI calls only configured local gateway/service HTTP boundaries.",
        },
        "rows": rows,
        "summary": _summary(rows),
    }


def write_outputs(*, output_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "live_validation_dashboard.json"
    html_path = output_dir / "live_validation_dashboard.html"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    html_path.write_text(_render_html(report), encoding="utf-8")
    return {"json": str(json_path), "html": str(html_path)}


def _deterministic_contract_row() -> dict[str, Any]:
    contract = PROJECT_ROOT / "config" / "narrative_service_contract.yaml"
    return {
        "group": "deterministic_local",
        "capability": "narrative_service_contract_file",
        "mode": "deterministic_local",
        "status": "passed" if contract.exists() else "system_failure",
        "status_label_zh": "已通过" if contract.exists() else "系统失败",
        "source": "repo",
        "endpoint": str(contract),
        "latency_ms": 0,
        "row_count": 1 if contract.exists() else 0,
        "warnings": [],
        "message": "Narrative Service contract exists in repo.",
    }


def _gateway_configuration_row(*, gateway_url: str) -> dict[str, Any]:
    configured = bool(gateway_url.strip())
    return {
        "group": "gateway_health",
        "capability": "gateway_configuration",
        "mode": "live_provider",
        "status": "passed" if configured else "not_configured",
        "status_label_zh": "已配置" if configured else "缺少配置",
        "source": "MARKET_DATA_GATEWAY_URL",
        "endpoint": gateway_url.strip(),
        "latency_ms": 0,
        "row_count": 1 if configured else 0,
        "warnings": [],
        "message": "Gateway URL configured." if configured else "MARKET_DATA_GATEWAY_URL is not configured.",
    }


def _combined_gateway_row(
    *,
    base_url: str,
    timeout_seconds: float,
    trade_date: str,
    fetch_json: FetchJson,
) -> dict[str, Any]:
    checks = [
        _probe_row(
            group="sector_flow_structure_news",
            capability="gateway_sector_constituents",
            mode="live_provider",
            base_url=base_url,
            method="GET",
            path="/api/v1/market-data/sectors/constituents",
            query={"sector_name": "白酒"},
            timeout_seconds=timeout_seconds,
            fetch_json=fetch_json,
        ),
        _probe_row(
            group="sector_flow_structure_news",
            capability="gateway_northbound_capital",
            mode="live_provider",
            base_url=base_url,
            method="GET",
            path="/api/v1/market-data/capital/northbound",
            query={"trade_date": trade_date},
            timeout_seconds=timeout_seconds,
            fetch_json=fetch_json,
        ),
        _probe_row(
            group="sector_flow_structure_news",
            capability="gateway_index_constituents",
            mode="live_provider",
            base_url=base_url,
            method="GET",
            path="/api/v1/market-data/index/constituents",
            query={"index_code": "000300.SH"},
            timeout_seconds=timeout_seconds,
            fetch_json=fetch_json,
        ),
        _probe_row(
            group="sector_flow_structure_news",
            capability="gateway_news_briefs",
            mode="live_provider",
            base_url=base_url,
            method="GET",
            path="/api/v1/market-data/news/briefs",
            query={"limit": 3},
            timeout_seconds=timeout_seconds,
            fetch_json=fetch_json,
        ),
    ]
    statuses = {item["status"] for item in checks}
    if statuses == {"not_configured"}:
        status = "not_configured"
    elif "system_failure" in statuses:
        status = "system_failure"
    elif "blocked" in statuses:
        status = "blocked"
    elif "degraded" in statuses:
        status = "degraded"
    elif statuses == {"product_gap"}:
        status = "product_gap"
    else:
        status = "passed"
    return {
        "group": "sector_flow_structure_news",
        "capability": "gateway_sector_flow_structure_news",
        "mode": "live_provider",
        "status": status,
        "status_label_zh": _status_label(status),
        "source": "MARKET_DATA_GATEWAY_URL",
        "endpoint": "combined gateway sector/flow/structure/news probes",
        "latency_ms": sum(int(item.get("latency_ms") or 0) for item in checks),
        "row_count": sum(int(item.get("row_count") or 0) for item in checks),
        "warnings": [warning for item in checks for warning in _list(item.get("warnings"))],
        "message": "; ".join(str(item.get("message") or "") for item in checks if item.get("message")),
        "checks": checks,
    }


def _probe_row(
    *,
    group: str,
    capability: str,
    mode: str,
    base_url: str,
    method: str,
    path: str,
    timeout_seconds: float,
    fetch_json: FetchJson,
    query: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url = base_url.strip().rstrip("/")
    if not base_url:
        return {
            "group": group,
            "capability": capability,
            "mode": mode,
            "status": "not_configured",
            "status_label_zh": _status_label("not_configured"),
            "source": "configured_http_boundary",
            "endpoint": path,
            "latency_ms": 0,
            "row_count": 0,
            "warnings": [],
            "message": "Required local service URL is not configured.",
        }
    url = _url(base_url=base_url, path=path, query=query)
    started_at = perf_counter()
    try:
        status_code, response = fetch_json(
            method=method,
            url=url,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
    except TimeoutError as exc:
        return _failure_row(group, capability, mode, url, started_at, f"timeout: {exc}")
    except OSError as exc:
        return _failure_row(group, capability, mode, url, started_at, str(exc))
    except Exception as exc:  # pragma: no cover - defensive boundary
        return _failure_row(group, capability, mode, url, started_at, str(exc))
    latency_ms = int((perf_counter() - started_at) * 1000)
    row_count = _row_count(response)
    warnings = _warnings(response)
    status = _classify_response(
        http_status=status_code,
        payload=response,
        row_count=row_count,
        warnings=warnings,
    )
    return {
        "group": group,
        "capability": capability,
        "mode": mode,
        "status": status,
        "status_label_zh": _status_label(status),
        "source": base_url,
        "endpoint": url,
        "latency_ms": latency_ms,
        "row_count": row_count,
        "warnings": warnings,
        "message": _message(status, row_count=row_count, warnings=warnings),
    }


def _classify_response(
    *,
    http_status: int,
    payload: dict[str, Any],
    row_count: int,
    warnings: list[dict[str, Any]],
) -> str:
    if http_status >= 500:
        return "system_failure"
    if http_status in {401, 403, 429} or 400 <= http_status < 500:
        return "blocked"
    status = str(payload.get("status") or "").lower()
    if status in {"degraded", "partial"} or warnings:
        return "degraded"
    if status in {"missing", "not_found"}:
        return "product_gap"
    if row_count == 0 and "data" in payload:
        return "product_gap"
    return "passed"


def _failure_row(
    group: str,
    capability: str,
    mode: str,
    endpoint: str,
    started_at: float,
    message: str,
) -> dict[str, Any]:
    return {
        "group": group,
        "capability": capability,
        "mode": mode,
        "status": "system_failure",
        "status_label_zh": _status_label("system_failure"),
        "source": "configured_http_boundary",
        "endpoint": endpoint,
        "latency_ms": int((perf_counter() - started_at) * 1000),
        "row_count": 0,
        "warnings": [{"code": "SYSTEM_FAILURE", "message": message}],
        "message": message,
    }


def _fetch_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
        payload_obj = json.loads(raw) if raw else {}
        if not isinstance(payload_obj, dict):
            payload_obj = {"data": payload_obj}
        return int(response.status), payload_obj


def _url(*, base_url: str, path: str, query: dict[str, Any] | None = None) -> str:
    url = urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def _row_count(payload: dict[str, Any]) -> int:
    if str(payload.get("status") or "").lower() == "ok" and "data" not in payload:
        return 1
    data = payload.get("data")
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("rows", "items", "packs", "narratives", "mappings"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
        if data:
            return 1
    return 0


def _warnings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = payload.get("warnings")
    return warnings if isinstance(warnings, list) else []


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {status: 0 for status in STATUS_TAXONOMY}
    for row in rows:
        status = str(row.get("status") or "")
        if status in counts:
            counts[status] += 1
    system_failure_count = counts["system_failure"]
    return {
        "overall_status": "system_failure" if system_failure_count else "completed",
        "status_counts": counts,
        "system_failure_count": system_failure_count,
        "not_configured_count": counts["not_configured"],
        "degraded_count": counts["degraded"],
        "product_gap_count": counts["product_gap"],
        "deterministic_check_count": sum(1 for row in rows if row.get("mode") == "deterministic_local"),
        "live_provider_check_count": sum(1 for row in rows if row.get("mode") == "live_provider"),
    }


def _render_html(report: dict[str, Any]) -> str:
    rows = [
        "<tr>"
        f"<td>{_html(row.get('group'))}</td>"
        f"<td>{_html(row.get('capability'))}</td>"
        f"<td><code>{_html(row.get('status'))}</code> {_html(row.get('status_label_zh'))}</td>"
        f"<td>{_html(row.get('mode'))}</td>"
        f"<td>{_html(row.get('row_count'))}</td>"
        f"<td>{_html(row.get('message'))}</td>"
        "</tr>"
        for row in _list(report.get("rows"))
    ]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>实时验证看板</title>",
            "<style>",
            "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f7f8fa;color:#20242b}",
            "main{max-width:1180px;margin:0 auto;padding:28px}",
            "table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9dee7}",
            "th,td{border-bottom:1px solid #e4e8ef;padding:9px;text-align:left;vertical-align:top}",
            "code{background:#eef2f7;padding:2px 5px}",
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            "<h1>实时验证看板</h1>",
            f"<p>生成时间: {_html(report.get('generated_at'))}</p>",
            f"<p>整体状态: <code>{_html(_mapping(report.get('summary')).get('overall_status'))}</code></p>",
            "<table><thead><tr><th>分组</th><th>能力</th><th>状态</th><th>模式</th><th>行数</th><th>说明</th></tr></thead><tbody>",
            *(rows or ['<tr><td colspan="6">无验证结果</td></tr>']),
            "</tbody></table>",
            "<section><h2>状态口径</h2>",
            "<p>缺少配置会标记为 <code>not_configured</code> / 缺少配置，不视为系统失败。</p>",
            "<p>FNI 只调用已配置的本地 gateway 或 Narrative Service HTTP 边界，不直接调用外部数据源。</p>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _message(status: str, *, row_count: int, warnings: list[dict[str, Any]]) -> str:
    if status == "passed":
        return f"Probe returned usable payload data; row_count={row_count}."
    if status == "degraded":
        return f"Probe returned degraded payload or warnings; warning_count={len(warnings)}."
    if status == "product_gap":
        return "Service reachable, but requested business data is empty or missing."
    if status == "blocked":
        return "Configured endpoint rejected or blocked the request."
    if status == "not_configured":
        return "Required URL is not configured."
    return "Probe failed at runtime."


def _status_label(status: str) -> str:
    return {
        "passed": "已通过",
        "degraded": "降级",
        "blocked": "受阻",
        "not_configured": "缺少配置",
        "product_gap": "产品数据缺口",
        "system_failure": "系统失败",
    }.get(status, status)


def _default_output_dir() -> Path:
    timestamp = _now().replace(":", "").replace("+", "Z")
    return DEFAULT_OUTPUT_DIR / "live_validation_dashboard" / timestamp


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _html(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
