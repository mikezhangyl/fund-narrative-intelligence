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
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402

STATUS_TAXONOMY = [
    "configured",
    "not_configured",
    "reachable",
    "provider_permission_required",
    "request_timeout",
    "upstream_degraded",
    "schema_mismatch",
    "contract_failed",
    "success",
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
                "contract_failed_count": report["summary"]["contract_failed_count"],
                "action_required_count": report["summary"]["action_required_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


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
            "aliases": {
                "not_configured": ["missing_config", "missing_url"],
                "success": ["passed"],
                "upstream_degraded": ["degraded"],
                "provider_permission_required": ["blocked", "permission_required"],
                "contract_failed": ["system_failure"],
            },
            "rules": {
                "configured": "Required local boundary configuration exists; no secret value is returned.",
                "not_configured": "Required local gateway or Narrative Service URL is absent.",
                "reachable": "Configured boundary responded, but no business contract was evaluated.",
                "provider_permission_required": "Provider or gateway route requires permission, credential, quota, or authorization.",
                "request_timeout": "Bounded request timed out without failing the whole smoke run.",
                "upstream_degraded": "Configured boundary returned degraded payload, warnings, or upstream instability.",
                "schema_mismatch": "Configured boundary responded with an unexpected or empty contract shape.",
                "contract_failed": "Configured boundary failed the expected HTTP or JSON contract.",
                "success": "Configured probe returned usable payload data.",
            },
        },
        "inputs": {
            "gateway_url_configured": bool(gateway_url.strip()),
            "service_url_configured": bool(service_url.strip()),
            "gateway_url": _redact_url(gateway_url.strip()),
            "service_url": _redact_url(service_url.strip()),
            "secrets_redacted": True,
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
    status = "success" if contract.exists() else "contract_failed"
    return {
        "id": "deterministic_local.narrative_service_contract_file",
        "group": "deterministic_local",
        "capability": "narrative_service_contract_file",
        "owner_service": "fni",
        "mode": "deterministic_local",
        "status": status,
        "status_label_zh": _status_label(status),
        "source": "repo",
        "endpoint": str(contract),
        "required_credential_hint": "none",
        "latency_ms": 0,
        "row_count": 1 if contract.exists() else 0,
        "warnings": [],
        "failure_reason": None if contract.exists() else "contract_file_missing",
        "next_action": _next_action(status, owner_service="fni"),
        "message": "Narrative Service contract exists in repo."
        if contract.exists()
        else "Narrative Service contract file is missing.",
    }


def _gateway_configuration_row(*, gateway_url: str) -> dict[str, Any]:
    configured = bool(gateway_url.strip())
    status = "configured" if configured else "not_configured"
    return {
        "id": "gateway_health.gateway_configuration",
        "group": "gateway_health",
        "capability": "gateway_configuration",
        "owner_service": "stock-data-gateway",
        "mode": "live_provider",
        "status": status,
        "status_label_zh": _status_label(status),
        "source": "MARKET_DATA_GATEWAY_URL",
        "endpoint": _redact_url(gateway_url.strip()),
        "required_credential_hint": "MARKET_DATA_GATEWAY_URL",
        "latency_ms": 0,
        "row_count": 1 if configured else 0,
        "warnings": [],
        "failure_reason": None if configured else "missing_config: MARKET_DATA_GATEWAY_URL",
        "next_action": _next_action(status, owner_service="stock-data-gateway"),
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
    elif "contract_failed" in statuses:
        status = "contract_failed"
    elif "request_timeout" in statuses:
        status = "request_timeout"
    elif "provider_permission_required" in statuses:
        status = "provider_permission_required"
    elif "upstream_degraded" in statuses:
        status = "upstream_degraded"
    elif "schema_mismatch" in statuses:
        status = "schema_mismatch"
    else:
        status = "success"
    owner_service = "stock-data-gateway"
    return {
        "id": "sector_flow_structure_news.gateway_sector_flow_structure_news",
        "group": "sector_flow_structure_news",
        "capability": "gateway_sector_flow_structure_news",
        "owner_service": owner_service,
        "mode": "live_provider",
        "status": status,
        "status_label_zh": _status_label(status),
        "source": "MARKET_DATA_GATEWAY_URL",
        "endpoint": "combined gateway sector/flow/structure/news probes",
        "required_credential_hint": "gateway-managed provider credentials",
        "latency_ms": sum(int(item.get("latency_ms") or 0) for item in checks),
        "row_count": sum(int(item.get("row_count") or 0) for item in checks),
        "warnings": [warning for item in checks for warning in _list(item.get("warnings"))],
        "failure_reason": _combined_failure_reason(checks),
        "next_action": _next_action(status, owner_service=owner_service),
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
    base_url = _clean_base_url(base_url)
    owner_service = _owner_service(group=group, capability=capability)
    if not base_url:
        status = "not_configured"
        return {
            "id": f"{group}.{capability}",
            "group": group,
            "capability": capability,
            "owner_service": owner_service,
            "mode": mode,
            "status": status,
            "status_label_zh": _status_label(status),
            "source": "configured_http_boundary",
            "endpoint": path,
            "required_credential_hint": _credential_hint(owner_service=owner_service, capability=capability),
            "latency_ms": 0,
            "row_count": 0,
            "warnings": [],
            "failure_reason": "missing_config: configured local service URL",
            "next_action": _next_action(status, owner_service=owner_service),
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
        return _failure_row(group, capability, mode, url, started_at, f"timeout: {exc}", "request_timeout")
    except OSError as exc:
        return _failure_row(group, capability, mode, url, started_at, str(exc), "contract_failed")
    except Exception as exc:  # pragma: no cover - defensive boundary
        return _failure_row(group, capability, mode, url, started_at, str(exc), "contract_failed")
    latency_ms = int((perf_counter() - started_at) * 1000)
    row_count = _row_count(response)
    warnings = _warnings(response)
    status = _classify_response(
        http_status=status_code,
        payload=response,
        row_count=row_count,
        warnings=warnings,
    )
    failure_reason = _failure_reason(
        status=status,
        http_status=status_code,
        payload=response,
        warnings=warnings,
    )
    return {
        "id": f"{group}.{capability}",
        "group": group,
        "capability": capability,
        "owner_service": owner_service,
        "mode": mode,
        "status": status,
        "status_label_zh": _status_label(status),
        "source": _redact_url(base_url),
        "endpoint": _redact_url(url),
        "required_credential_hint": _credential_hint(owner_service=owner_service, capability=capability),
        "latency_ms": latency_ms,
        "row_count": row_count,
        "warnings": warnings,
        "failure_reason": failure_reason,
        "next_action": _next_action(status, owner_service=owner_service),
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
        return "upstream_degraded"
    if http_status in {408, 504}:
        return "request_timeout"
    if http_status in {401, 403, 429}:
        return "provider_permission_required"
    if 400 <= http_status < 500:
        return "contract_failed"
    status = str(payload.get("status") or "").lower()
    if status in {"degraded", "partial"} or warnings:
        return "upstream_degraded"
    if status in {"missing", "not_found"}:
        return "schema_mismatch"
    if row_count == 0 and "data" in payload:
        return "schema_mismatch"
    return "success"


def _failure_row(
    group: str,
    capability: str,
    mode: str,
    endpoint: str,
    started_at: float,
    message: str,
    status: str,
) -> dict[str, Any]:
    owner_service = _owner_service(group=group, capability=capability)
    return {
        "id": f"{group}.{capability}",
        "group": group,
        "capability": capability,
        "owner_service": owner_service,
        "mode": mode,
        "status": status,
        "status_label_zh": _status_label(status),
        "source": "configured_http_boundary",
        "endpoint": _redact_url(endpoint),
        "required_credential_hint": _credential_hint(owner_service=owner_service, capability=capability),
        "latency_ms": int((perf_counter() - started_at) * 1000),
        "row_count": 0,
        "warnings": [{"code": status.upper(), "message": message}],
        "failure_reason": message,
        "next_action": _next_action(status, owner_service=owner_service),
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
    action_required_statuses = {
        "not_configured",
        "provider_permission_required",
        "request_timeout",
        "upstream_degraded",
        "schema_mismatch",
        "contract_failed",
    }
    action_required_count = sum(counts[status] for status in action_required_statuses)
    return {
        "overall_status": "completed_with_actions" if action_required_count else "completed",
        "status_counts": counts,
        "contract_failed_count": counts["contract_failed"],
        "action_required_count": action_required_count,
        "not_configured_count": counts["not_configured"],
        "upstream_degraded_count": counts["upstream_degraded"],
        "request_timeout_count": counts["request_timeout"],
        "provider_permission_required_count": counts["provider_permission_required"],
        "deterministic_check_count": sum(1 for row in rows if row.get("mode") == "deterministic_local"),
        "live_provider_check_count": sum(1 for row in rows if row.get("mode") == "live_provider"),
    }


def _render_html(report: dict[str, Any]) -> str:
    rows = [
        "<tr>"
        f"<td>{_html(row.get('group'))}</td>"
        f"<td>{_html(row.get('capability'))}</td>"
        f"<td>{_html(row.get('owner_service'))}</td>"
        f"<td><code>{_html(row.get('status'))}</code> {_html(row.get('status_label_zh'))}</td>"
        f"<td>{_html(row.get('mode'))}</td>"
        f"<td>{_html(row.get('row_count'))}</td>"
        f"<td>{_html(row.get('message'))}</td>"
        f"<td>{_html(_mapping(row.get('next_action')).get('description'))}</td>"
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
            "<table><thead><tr><th>分组</th><th>能力</th><th>归属</th><th>状态</th><th>模式</th><th>行数</th><th>说明</th><th>下一步</th></tr></thead><tbody>",
            *(rows or ['<tr><td colspan="8">无验证结果</td></tr>']),
            "</tbody></table>",
            "<section><h2>状态口径</h2>",
            "<p>缺少配置会标记为 <code>not_configured</code> / 缺少配置，不视为整次 smoke 失败。</p>",
            "<p>FNI 只调用已配置的本地 gateway 或 Narrative Service HTTP 边界，不直接调用外部数据源。</p>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _message(status: str, *, row_count: int, warnings: list[dict[str, Any]]) -> str:
    if status in {"success", "reachable"}:
        return f"Probe returned usable payload data; row_count={row_count}."
    if status == "configured":
        return "Required local boundary configuration is present."
    if status == "upstream_degraded":
        return f"Probe returned degraded payload or warnings; warning_count={len(warnings)}."
    if status == "schema_mismatch":
        return "Service reachable, but response shape or business data did not match the smoke contract."
    if status == "provider_permission_required":
        return "Configured endpoint requires provider permission, credential, quota, or authorization."
    if status == "request_timeout":
        return "Configured endpoint timed out inside the bounded smoke window."
    if status == "not_configured":
        return "Required URL is not configured."
    return "Probe failed the expected HTTP or JSON contract."


def _status_label(status: str) -> str:
    return {
        "configured": "已配置",
        "not_configured": "缺少配置",
        "reachable": "可连通",
        "provider_permission_required": "需要权限",
        "request_timeout": "请求超时",
        "upstream_degraded": "上游降级",
        "schema_mismatch": "契约不匹配",
        "contract_failed": "契约失败",
        "success": "成功",
    }.get(status, status)


def _failure_reason(
    *,
    status: str,
    http_status: int,
    payload: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> str | None:
    if status in {"configured", "reachable", "success"}:
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        code = str(error.get("code") or "").strip()
        message = str(error.get("message") or "").strip()
        if code or message:
            return ": ".join(item for item in (code, message) if item)
    if warnings:
        code = str(warnings[0].get("code") or "").strip()
        message = str(warnings[0].get("message") or "").strip()
        return ": ".join(item for item in (code, message) if item) or status
    return f"http_status={http_status}"


def _combined_failure_reason(checks: list[dict[str, Any]]) -> str | None:
    reasons = [
        str(item.get("failure_reason"))
        for item in checks
        if item.get("failure_reason")
    ]
    return "; ".join(reasons) if reasons else None


def _owner_service(*, group: str, capability: str) -> str:
    if group == "deterministic_local":
        return "fni"
    if "narrative" in group or "narrative" in capability or "review" in group:
        return "narrative-service"
    return "stock-data-gateway"


def _credential_hint(*, owner_service: str, capability: str) -> str:
    if owner_service == "stock-data-gateway":
        if "tushare" in capability or "daily" in capability or "fund" in capability:
            return "MARKET_DATA_GATEWAY_URL plus gateway-managed Tushare permission; token value redacted"
        return "MARKET_DATA_GATEWAY_URL plus gateway-managed provider permission; secret values redacted"
    if owner_service == "narrative-service":
        return "NARRATIVE_SERVICE_URL; no service secret value returned"
    return "none"


def _next_action(status: str, *, owner_service: str) -> dict[str, str]:
    descriptions = {
        "configured": "Continue to endpoint smoke checks.",
        "not_configured": "Set the local service URL before relying on live provider output.",
        "reachable": "Add or run a business contract probe for this service.",
        "provider_permission_required": "Check provider credential, permission, quota, or gateway route policy.",
        "request_timeout": "Increase bounded timeout only after confirming route health and expected latency.",
        "upstream_degraded": "Inspect gateway/provider warnings and retry after upstream recovery.",
        "schema_mismatch": "Compare response payload with the documented smoke contract.",
        "contract_failed": "Fix the owning service HTTP/JSON contract before downstream runs.",
        "success": "No action required.",
    }
    return {
        "owner_service": owner_service,
        "description": descriptions.get(status, "Review the owning service diagnostics."),
    }


def _clean_base_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw
    cleaned = parsed._replace(query="", fragment="").geturl().rstrip("/")
    return cleaned


def _redact_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if not parsed.query:
        return value
    return parsed._replace(query="REDACTED").geturl()


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
