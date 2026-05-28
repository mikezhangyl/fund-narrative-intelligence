from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data.gateway_contract import (  # noqa: E402
    DEFAULT_GATEWAY_CONTRACT_PATH,
    GatewayContract,
    GatewayEndpointContract,
    load_gateway_contract,
    missing_required_fields,
    rows_from_path,
)

GatewayFetcher = Callable[[GatewayEndpointContract, str, float], tuple[int, dict[str, Any]]]
TushareFacadeFetcher = Callable[
    [GatewayEndpointContract, str, dict[str, Any], float],
    tuple[int, dict[str, Any]],
]

CONFORMANCE_MODES = ("normalized", "tushare-facade", "all")
TUSHARE_FACADE_SURFACE = "tushare_facade"
TUSHARE_FACADE_TOKEN = "local-gateway-token-ignored"
TUSHARE_RESPONSE_FIELD_BY_NORMALIZED = {
    "symbol": "ts_code",
    "volume": "vol",
}


@dataclass(frozen=True)
class GatewayConformanceCheck:
    endpoint_id: str
    provider: str
    dataset_id: str
    method: str
    path: str
    status: str
    http_status: int | None
    row_count: int
    missing_fields: tuple[str, ...]
    failure_reason: str | None = None
    unstable: bool = False
    maturity: str = "available"
    surface: str = "normalized"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a local market-data gateway against the project contract."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_GATEWAY_CONTRACT_PATH)
    parser.add_argument("--endpoint-id", action="append", default=None)
    parser.add_argument("--include-planned", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument(
        "--mode",
        choices=CONFORMANCE_MODES,
        default="normalized",
        help=(
            "Validation surface: normalized REST contract, Tushare-compatible "
            "facade, or both."
        ),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        dest="output_format",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = load_gateway_contract(args.contract)
    report = run_gateway_conformance(
        contract=contract,
        base_url=args.base_url,
        endpoint_ids=tuple(args.endpoint_id or ()),
        include_planned=args.include_planned,
        timeout_seconds=args.timeout_seconds,
        mode=args.mode,
    )
    rendered = render_report(report, output_format=args.output_format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0 if report["summary"]["failed_checks"] == 0 else 1


def run_gateway_conformance(
    *,
    contract: GatewayContract,
    base_url: str,
    endpoint_ids: tuple[str, ...] = (),
    include_planned: bool = False,
    timeout_seconds: float = 10.0,
    mode: str = "normalized",
    fetcher: GatewayFetcher | None = None,
    facade_fetcher: TushareFacadeFetcher | None = None,
) -> dict[str, Any]:
    if mode not in CONFORMANCE_MODES:
        raise ValueError(f"unsupported conformance mode: {mode}")
    endpoints = _selected_endpoints(
        contract=contract,
        endpoint_ids=endpoint_ids,
        include_planned=include_planned,
    )
    checks: list[GatewayConformanceCheck] = []
    if mode in ("normalized", "all"):
        checks.extend(
            _run_check(
                endpoint=endpoint,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                fetcher=fetcher or _http_fetch,
            )
            for endpoint in endpoints
        )
    if mode in ("tushare-facade", "all"):
        checks.extend(
            _run_tushare_facade_check(
                endpoint=endpoint,
                base_url=base_url,
                facade_path=_tushare_facade_path(contract),
                timeout_seconds=timeout_seconds,
                fetcher=facade_fetcher or _http_tushare_facade_fetch,
            )
            for endpoint in endpoints
            if endpoint.provider == "tushare"
        )
    failed = [check for check in checks if check.status != "passed"]
    return {
        "version": "market-data-gateway-conformance-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "base_url": base_url,
        "contract_version": contract.version,
        "mode": mode,
        "summary": {
            "total_checks": len(checks),
            "passed_checks": len(checks) - len(failed),
            "failed_checks": len(failed),
        },
        "checks": [check.to_dict() for check in checks],
    }


def render_report(report: dict[str, Any], *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output_format != "markdown":
        raise ValueError(f"unsupported output format: {output_format}")
    return _markdown_report(report)


def _selected_endpoints(
    *,
    contract: GatewayContract,
    endpoint_ids: tuple[str, ...],
    include_planned: bool,
) -> tuple[GatewayEndpointContract, ...]:
    endpoints = (
        tuple(contract.endpoint(endpoint_id) for endpoint_id in endpoint_ids)
        if endpoint_ids
        else contract.endpoints
    )
    if include_planned:
        return endpoints
    return tuple(endpoint for endpoint in endpoints if endpoint.maturity != "planned")


def _run_check(
    *,
    endpoint: GatewayEndpointContract,
    base_url: str,
    timeout_seconds: float,
    fetcher: GatewayFetcher,
) -> GatewayConformanceCheck:
    try:
        http_status, payload = fetcher(endpoint, base_url, timeout_seconds)
        if http_status < 200 or http_status >= 300:
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                failure_reason=f"unexpected HTTP status {http_status}",
            )
        if not isinstance(payload, dict):
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                failure_reason="response must be a JSON object",
            )
        rows = rows_from_path(payload, endpoint.rows_path)
        row_failure = _minimum_row_failure(endpoint=endpoint, row_count=len(rows))
        if row_failure is not None:
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                row_count=len(rows),
                failure_reason=row_failure,
            )
        missing = missing_required_fields(rows, endpoint.required_response_fields)
        if missing:
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                row_count=len(rows),
                missing_fields=tuple(missing),
                failure_reason=f"missing required response fields: {', '.join(missing)}",
            )
        return GatewayConformanceCheck(
            endpoint_id=endpoint.endpoint_id,
            provider=endpoint.provider,
            dataset_id=endpoint.dataset_id,
            method=endpoint.method,
            path=endpoint.path,
            status="passed",
            http_status=http_status,
            row_count=len(rows),
            missing_fields=(),
            unstable=endpoint.unstable,
            maturity=endpoint.maturity,
        )
    except Exception as exc:
        return _failed_check(endpoint=endpoint, failure_reason=str(exc))


def _failed_check(
    *,
    endpoint: GatewayEndpointContract,
    failure_reason: str,
    http_status: int | None = None,
    row_count: int = 0,
    missing_fields: tuple[str, ...] = (),
    method: str | None = None,
    path: str | None = None,
    surface: str = "normalized",
) -> GatewayConformanceCheck:
    return GatewayConformanceCheck(
        endpoint_id=endpoint.endpoint_id,
        provider=endpoint.provider,
        dataset_id=endpoint.dataset_id,
        method=method or endpoint.method,
        path=path or endpoint.path,
        status="failed",
        http_status=http_status,
        row_count=row_count,
        missing_fields=missing_fields,
        failure_reason=failure_reason,
        unstable=endpoint.unstable,
        maturity=endpoint.maturity,
        surface=surface,
    )


def _http_fetch(
    endpoint: GatewayEndpointContract,
    base_url: str,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    url = _endpoint_url(endpoint=endpoint, base_url=base_url)
    body: bytes | None = None
    headers = {"Accept": "application/json"}
    if endpoint.method == "POST":
        body = json.dumps(endpoint.sample_request.get("json") or {}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=endpoint.method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return int(response.status), payload
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"code": "http_error", "message": str(exc)}}
        return int(exc.code), payload
    except (OSError, URLError) as exc:
        raise RuntimeError(f"gateway request failed: {exc}") from exc


def _endpoint_url(*, endpoint: GatewayEndpointContract, base_url: str) -> str:
    url = urljoin(base_url.rstrip("/") + "/", endpoint.path.lstrip("/"))
    query = endpoint.sample_request.get("query")
    if endpoint.method == "GET" and isinstance(query, dict) and query:
        return f"{url}?{urlencode(query)}"
    return url


def _run_tushare_facade_check(
    *,
    endpoint: GatewayEndpointContract,
    base_url: str,
    facade_path: str,
    timeout_seconds: float,
    fetcher: TushareFacadeFetcher,
) -> GatewayConformanceCheck:
    method = "POST"
    try:
        url = urljoin(base_url.rstrip("/") + "/", facade_path.lstrip("/"))
        request_body = _tushare_facade_request_body(endpoint)
        http_status, payload = fetcher(endpoint, url, request_body, timeout_seconds)
        if http_status < 200 or http_status >= 300:
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                failure_reason=f"unexpected HTTP status {http_status}",
                method=method,
                path=facade_path,
                surface=TUSHARE_FACADE_SURFACE,
            )
        if not isinstance(payload, dict):
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                failure_reason="response must be a JSON object",
                method=method,
                path=facade_path,
                surface=TUSHARE_FACADE_SURFACE,
            )
        if payload.get("code") not in (0, None):
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                failure_reason=f"tushare facade returned code {payload.get('code')}",
                method=method,
                path=facade_path,
                surface=TUSHARE_FACADE_SURFACE,
            )
        rows = _tushare_facade_rows(payload)
        row_failure = _minimum_row_failure(endpoint=endpoint, row_count=len(rows))
        if row_failure is not None:
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                row_count=len(rows),
                failure_reason=row_failure,
                method=method,
                path=facade_path,
                surface=TUSHARE_FACADE_SURFACE,
            )
        required_fields = _tushare_facade_required_response_fields(endpoint)
        missing = missing_required_fields(rows, required_fields)
        if missing:
            return _failed_check(
                endpoint=endpoint,
                http_status=http_status,
                row_count=len(rows),
                missing_fields=tuple(missing),
                failure_reason=f"missing required response fields: {', '.join(missing)}",
                method=method,
                path=facade_path,
                surface=TUSHARE_FACADE_SURFACE,
            )
        return GatewayConformanceCheck(
            endpoint_id=endpoint.endpoint_id,
            provider=endpoint.provider,
            dataset_id=endpoint.dataset_id,
            method=method,
            path=facade_path,
            status="passed",
            http_status=http_status,
            row_count=len(rows),
            missing_fields=(),
            unstable=endpoint.unstable,
            maturity=endpoint.maturity,
            surface=TUSHARE_FACADE_SURFACE,
        )
    except Exception as exc:
        return _failed_check(
            endpoint=endpoint,
            failure_reason=str(exc),
            method=method,
            path=facade_path,
            surface=TUSHARE_FACADE_SURFACE,
        )


def _http_tushare_facade_fetch(
    endpoint: GatewayEndpointContract,
    url: str,
    request_body: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    del endpoint
    request = Request(
        url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return int(response.status), payload
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"code": "http_error", "message": str(exc)}}
        return int(exc.code), payload
    except (OSError, URLError) as exc:
        raise RuntimeError(f"gateway tushare facade request failed: {exc}") from exc


def _minimum_row_failure(
    *,
    endpoint: GatewayEndpointContract,
    row_count: int,
) -> str | None:
    if row_count < endpoint.minimum_rows:
        row_label = "row" if endpoint.minimum_rows == 1 else "rows"
        return f"expected at least {endpoint.minimum_rows} {row_label}; got {row_count}"
    return None


def _tushare_facade_path(contract: GatewayContract) -> str:
    compatibility = contract.compatibility.get("tushare_native_post")
    if not isinstance(compatibility, dict) or not compatibility.get("enabled"):
        raise ValueError("gateway contract does not enable tushare_native_post")
    if str(compatibility.get("method") or "").upper() != "POST":
        raise ValueError("tushare_native_post must use POST")
    path = str(compatibility.get("path") or "").strip()
    if not path:
        raise ValueError("tushare_native_post.path is required")
    return path


def _tushare_facade_request_body(endpoint: GatewayEndpointContract) -> dict[str, Any]:
    fields = _tushare_facade_required_response_fields(endpoint)
    return {
        "api_name": endpoint.endpoint,
        "token": TUSHARE_FACADE_TOKEN,
        "params": _tushare_facade_params(endpoint),
        "fields": ",".join(fields),
    }


def _tushare_facade_params(endpoint: GatewayEndpointContract) -> dict[str, Any]:
    sample = endpoint.sample_request.get("json") or endpoint.sample_request.get("query") or {}
    if not isinstance(sample, dict):
        return {}
    params: dict[str, Any] = {}
    for key, value in sample.items():
        if key == "symbols":
            params["ts_code"] = _comma_join(value)
        elif key in {"start_date", "end_date", "trade_date"}:
            params[key] = _compact_date_text(value)
        elif key in {"exchange", "list_status", "ts_code"}:
            params[key] = value
    return params


def _tushare_facade_required_response_fields(
    endpoint: GatewayEndpointContract,
) -> tuple[str, ...]:
    fields: list[str] = []
    for field in endpoint.required_response_fields:
        facade_field = TUSHARE_RESPONSE_FIELD_BY_NORMALIZED.get(field, field)
        if facade_field not in fields:
            fields.append(facade_field)
    return tuple(fields)


def _tushare_facade_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("tushare facade response missing data object")
    fields = data.get("fields")
    items = data.get("items")
    if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
        raise ValueError("tushare facade data.fields must be a string list")
    if not isinstance(items, list):
        raise ValueError("tushare facade data.items must be a list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            rows.append(item)
        elif isinstance(item, list):
            rows.append(dict(zip(fields, item, strict=False)))
        else:
            raise ValueError(f"tushare facade data.items[{index}] must be a list or object")
    return rows


def _comma_join(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _compact_date_text(value: Any) -> str:
    return str(value).replace("-", "")


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Market Data Gateway Conformance",
        "",
        f"- Base URL: `{report['base_url']}`",
        f"- Contract Version: `{report['contract_version']}`",
        f"- Mode: `{report.get('mode', 'normalized')}`",
        f"- Total Checks: `{summary['total_checks']}`",
        f"- Passed: `{summary['passed_checks']}`",
        f"- Failed: `{summary['failed_checks']}`",
        "",
        "| Endpoint | Surface | Provider | Dataset | Status | Rows | Failure |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            "| "
            f"{check['endpoint_id']} | "
            f"{check.get('surface', 'normalized')} | "
            f"{check['provider']} | "
            f"{check['dataset_id']} | "
            f"{check['status']} | "
            f"{check['row_count']} | "
            f"{check.get('failure_reason') or ''} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
