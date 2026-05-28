from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import local_env  # noqa: E402
from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.market_data.cache import NullMarketDataCache  # noqa: E402
from src.market_data.capabilities import (  # noqa: E402
    DataCapabilityRegistry,
    load_data_capability_registry,
)
from src.market_data.providers.akshare import AkShareMarketDataProvider  # noqa: E402
from src.market_data.providers.tushare import TushareMarketDataProvider  # noqa: E402
from src.market_data.validators import validate_records  # noqa: E402
from src.providers.eastmoney_market import EastmoneyMarketDataProvider  # noqa: E402


@dataclass(frozen=True)
class Probe:
    provider: str
    endpoint: str
    capability: str
    required_fields: set[str]
    operation: Callable[[], list[dict[str, Any]]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run low-volume live validation probes for V0 market data sources."
    )
    parser.add_argument("--trade-date", default="20260522")
    parser.add_argument("--stock-code", default="600519")
    parser.add_argument("--tushare-symbol", default="600519.SH")
    parser.add_argument("--index-symbol", default="000001.SH")
    parser.add_argument("--etf-symbol", default="510300.SH")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--interval-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    if args.repeat <= 0:
        parser.error("--repeat must be positive")
    if args.interval_seconds < 0:
        parser.error("--interval-seconds must be non-negative")

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_DIR
        / "market_data_live_validation"
        / generated_at.replace(":", "").replace("+", "Z")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    report = run_validation_series(
        trade_date=args.trade_date,
        stock_code=args.stock_code,
        tushare_symbol=args.tushare_symbol,
        index_symbol=args.index_symbol,
        etf_symbol=args.etf_symbol,
        generated_at=generated_at,
        repeat_count=args.repeat,
        interval_seconds=args.interval_seconds,
    )
    json_path = output_dir / "live_validation_report.json"
    md_path = output_dir / "live_validation_report.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_markdown_report(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


def run_validation_series(
    *,
    trade_date: str,
    stock_code: str,
    tushare_symbol: str,
    index_symbol: str,
    etf_symbol: str,
    generated_at: str,
    repeat_count: int = 1,
    interval_seconds: float = 0.0,
) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for index in range(repeat_count):
        if index > 0 and interval_seconds > 0:
            sleep(interval_seconds)
        reports.append(
            run_validation(
                trade_date=trade_date,
                stock_code=stock_code,
                tushare_symbol=tushare_symbol,
                index_symbol=index_symbol,
                etf_symbol=etf_symbol,
                generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            )
        )
    capability_registry = load_data_capability_registry()
    matrix = _annotate_status_matrix(
        _endpoint_status_matrix(reports),
        registry=capability_registry,
    )
    if repeat_count == 1:
        report = dict(reports[0])
        report["endpoint_status_matrix"] = matrix
        report["capability_registry_summary"] = capability_registry.summary()
        return report
    return {
        "version": "market-data-live-probe-series-v1",
        "generated_at": generated_at,
        "scope": "low_volume_endpoint_probe_series",
        "repeat_count": repeat_count,
        "interval_seconds": interval_seconds,
        "plan": reports[0]["plan"],
        "environment": reports[-1]["environment"],
        "windows": reports,
        "endpoint_status_matrix": matrix,
        "capability_registry_summary": capability_registry.summary(),
        "summary": _series_summary(matrix, repeat_count=repeat_count),
    }


def run_validation(
    *,
    trade_date: str,
    stock_code: str,
    tushare_symbol: str,
    index_symbol: str,
    etf_symbol: str,
    generated_at: str,
) -> dict[str, Any]:
    eastmoney = EastmoneyMarketDataProvider()
    no_cache = NullMarketDataCache()
    tushare = TushareMarketDataProvider(cache=no_cache)
    akshare = AkShareMarketDataProvider(cache=no_cache)
    probes = _build_probes(
        eastmoney=eastmoney,
        tushare=tushare,
        akshare=akshare,
        stock_code=stock_code,
        tushare_symbol=tushare_symbol,
        index_symbol=index_symbol,
        etf_symbol=etf_symbol,
        trade_date=trade_date,
    )
    checks = [_run_probe(probe) for probe in probes]
    return {
        "version": "market-data-live-probe-v1",
        "generated_at": generated_at,
        "scope": "low_volume_endpoint_probe",
        "plan": {
            "trade_date": trade_date,
            "stock_code": stock_code,
            "tushare_symbol": tushare_symbol,
            "index_symbol": index_symbol,
            "etf_symbol": etf_symbol,
        },
        "environment": {
            "tushare_token_configured": bool(local_env.get_config_value("TUSHARE_TOKEN")),
            "secrets_redacted": True,
            "python_version": platform.python_version(),
            "akshare_version": _optional_module_version("akshare"),
        },
        "checks": checks,
        "summary": _summary(checks),
    }


def _build_probes(
    *,
    eastmoney: EastmoneyMarketDataProvider,
    tushare: TushareMarketDataProvider,
    akshare: AkShareMarketDataProvider,
    stock_code: str,
    tushare_symbol: str,
    index_symbol: str,
    etf_symbol: str,
    trade_date: str,
) -> list[Probe]:
    plain_etf_symbol = etf_symbol.split(".", 1)[0]
    return [
        Probe(
            provider="eastmoney",
            endpoint="market_quote",
            capability="latest_stock_quotes",
            required_fields={"stock_code", "latest_price", "retrieved_at"},
            operation=lambda: _quotes(eastmoney.get_stock_quotes([stock_code])),
        ),
        Probe(
            provider="tushare",
            endpoint="stock_basic",
            capability="stock_metadata",
            required_fields={"ts_code", "symbol", "name"},
            operation=lambda: tushare.fetch_stock_metadata()[:10],
        ),
        Probe(
            provider="tushare",
            endpoint="trade_cal",
            capability="trade_calendar",
            required_fields={"exchange", "cal_date", "is_open"},
            operation=lambda: tushare.fetch_trade_calendar(
                exchange="SSE",
                start_date=trade_date,
                end_date=trade_date,
            ),
        ),
        Probe(
            provider="tushare",
            endpoint="daily",
            capability="a_share_daily_bars",
            required_fields={"symbol", "trade_date", "close", "volume"},
            operation=lambda: tushare.fetch_daily_bars(
                symbols=[tushare_symbol],
                start_date=trade_date,
                end_date=trade_date,
                include_turnover=False,
            ),
        ),
        Probe(
            provider="tushare",
            endpoint="daily_basic",
            capability="turnover_rate",
            required_fields={"symbol", "trade_date", "turnover_rate"},
            operation=lambda: tushare.fetch_daily_bars(
                symbols=[tushare_symbol],
                start_date=trade_date,
                end_date=trade_date,
                include_turnover=True,
            ),
        ),
        Probe(
            provider="tushare",
            endpoint="index_daily",
            capability="index_bars",
            required_fields={"symbol", "trade_date", "close"},
            operation=lambda: tushare.fetch_index_bars(
                symbols=[index_symbol],
                start_date=trade_date,
                end_date=trade_date,
            ),
        ),
        Probe(
            provider="tushare",
            endpoint="fund_daily",
            capability="etf_daily",
            required_fields={"symbol", "trade_date", "close"},
            operation=lambda: tushare.fetch_etf_data(
                symbols=[etf_symbol],
                start_date=trade_date,
                end_date=trade_date,
            ),
        ),
        Probe(
            provider="akshare",
            endpoint="stock_zh_a_hist",
            capability="a_share_daily_bars_fallback",
            required_fields={"symbol", "trade_date", "close", "volume"},
            operation=lambda: akshare.fetch_daily_bars(
                symbols=[stock_code],
                start_date=trade_date,
                end_date=trade_date,
            ),
        ),
        Probe(
            provider="akshare",
            endpoint="fund_etf_hist_em",
            capability="etf_daily_fallback",
            required_fields={"symbol", "trade_date", "close"},
            operation=lambda: akshare.fetch_etf_data(
                symbols=[plain_etf_symbol],
                start_date=trade_date,
                end_date=trade_date,
            ),
        ),
        Probe(
            provider="akshare",
            endpoint="stock_board_concept_name_em",
            capability="sector_concepts",
            required_fields={"sector_name", "pct_change", "source"},
            operation=lambda: akshare.fetch_sector_data(trade_date=trade_date),
        ),
        Probe(
            provider="akshare",
            endpoint="stock_zt_pool_em+stock_zt_pool_dtgc_em",
            capability="limit_up_down_stats",
            required_fields={"trade_date", "limit_up_count", "limit_down_count"},
            operation=lambda: [akshare.fetch_limit_up_down_stats(trade_date=trade_date)],
        ),
    ]


def _run_probe(probe: Probe) -> dict[str, Any]:
    started = perf_counter()
    try:
        rows = probe.operation()
        latency_ms = round((perf_counter() - started) * 1000, 3)
        validation = validate_records(
            source=probe.provider,
            endpoint=probe.endpoint,
            records=rows,
            required_fields=probe.required_fields,
            latency_ms=latency_ms,
        ).to_dict()
        failure_reason = None
    except Exception as exc:
        rows = []
        latency_ms = round((perf_counter() - started) * 1000, 3)
        failure_reason = str(exc)
        validation = validate_records(
            source=probe.provider,
            endpoint=probe.endpoint,
            records=[],
            required_fields=probe.required_fields,
            latency_ms=latency_ms,
            failure_reason=failure_reason,
        ).to_dict()
    return {
        **validation,
        "capability": probe.capability,
        "row_count": len(rows),
        "rate_limit_risk": _rate_limit_risk(
            provider=probe.provider,
            endpoint=probe.endpoint,
            failure_reason=failure_reason,
        ),
        "anti_bot_risk": _anti_bot_risk(
            provider=probe.provider,
            endpoint=probe.endpoint,
            failure_reason=failure_reason,
        ),
        "operational_cost": _operational_cost(probe.provider, failure_reason),
    }


def _quotes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    quotes = payload.get("quotes")
    if not isinstance(quotes, list):
        raise ValueError("quote payload missing quotes list")
    return [dict(item) for item in quotes if isinstance(item, dict)]


def _optional_module_version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "unknown"))


def _rate_limit_risk(
    *,
    provider: str,
    endpoint: str,
    failure_reason: str | None,
) -> str:
    reason = (failure_reason or "").lower()
    if any(marker in reason for marker in ("rate", "throttle", "too many", "频繁", "限流")):
        return "high"
    if provider == "tushare":
        return "medium_token_quota_dependent"
    if provider == "akshare":
        return "medium_public_web_endpoint"
    if provider == "eastmoney":
        return "medium_public_web_endpoint"
    return "unknown"


def _anti_bot_risk(
    *,
    provider: str,
    endpoint: str,
    failure_reason: str | None,
) -> str:
    reason = (failure_reason or "").lower()
    if any(
        marker in reason
        for marker in ("proxyerror", "remotedisconnected", "captcha", "blocked", "403")
    ):
        return "high_observed_connection_or_blocking_failure"
    if provider == "tushare":
        return "low_token_api"
    if provider in {"akshare", "eastmoney"}:
        return "medium_public_web_endpoint"
    return "unknown"


def _operational_cost(provider: str, failure_reason: str | None) -> str:
    reason = failure_reason or ""
    if "TUSHARE_TOKEN" in reason:
        return "requires_token"
    if any(marker in reason for marker in ("积分", "权限", "permission")):
        return "requires_paid_or_point_access"
    if provider == "tushare":
        return "token_and_point_policy_dependent"
    return "no_direct_api_fee_observed"


def _summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    available = [check for check in checks if check["availability"] is True]
    failed = [check for check in checks if check["availability"] is False]
    high_anti_bot = [
        check for check in checks if str(check["anti_bot_risk"]).startswith("high")
    ]
    return {
        "total_checks": len(checks),
        "available_checks": len(available),
        "failed_checks": len(failed),
        "high_anti_bot_risk_checks": len(high_anti_bot),
        "available_capabilities": [check["capability"] for check in available],
        "failed_capabilities": [check["capability"] for check in failed],
    }


def _endpoint_status_matrix(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for report in reports:
        for check in report["checks"]:
            key = (
                str(check["source"]),
                str(check["endpoint"]),
                str(check["capability"]),
            )
            grouped.setdefault(key, []).append(check)

    matrix: list[dict[str, Any]] = []
    for (source, endpoint, capability), checks in sorted(grouped.items()):
        successes = [check for check in checks if check.get("availability") is True]
        failures = [check for check in checks if check.get("availability") is False]
        latency_values = [
            float(check["latency_ms"])
            for check in successes
            if isinstance(check.get("latency_ms"), int | float)
        ]
        matrix.append(
            {
                "source": source,
                "endpoint": endpoint,
                "capability": capability,
                "status": _endpoint_status(
                    source=source,
                    capability=capability,
                    success_count=len(successes),
                    total_count=len(checks),
                ),
                "success_count": len(successes),
                "failure_count": len(failures),
                "total_count": len(checks),
                "success_rate": round(len(successes) / len(checks), 4)
                if checks
                else 0.0,
                "min_latency_ms": min(latency_values) if latency_values else None,
                "max_latency_ms": max(latency_values) if latency_values else None,
                "max_row_count": max(
                    (int(check.get("row_count") or 0) for check in checks),
                    default=0,
                ),
                "anti_bot_risks": sorted(
                    {str(check.get("anti_bot_risk")) for check in checks}
                ),
                "rate_limit_risks": sorted(
                    {str(check.get("rate_limit_risk")) for check in checks}
                ),
                "failure_sample": _first_failure_sample(failures),
            }
        )
    return matrix


def _annotate_status_matrix(
    matrix: list[dict[str, Any]],
    *,
    registry: DataCapabilityRegistry,
) -> list[dict[str, Any]]:
    return registry.annotate_probe_matrix(matrix)


def _endpoint_status(
    *,
    source: str,
    capability: str,
    success_count: int,
    total_count: int,
) -> str:
    if total_count == 0 or success_count == 0:
        return "disabled"
    if success_count < total_count:
        return "unstable"
    if source in {"tushare", "eastmoney"} and not capability.endswith("_fallback"):
        return "primary"
    return "fallback"


def _first_failure_sample(failures: list[dict[str, Any]]) -> str | None:
    for failure in failures:
        reason = failure.get("failure_reason")
        if reason:
            return _short_failure(reason)
    return None


def _series_summary(
    matrix: list[dict[str, Any]],
    *,
    repeat_count: int,
) -> dict[str, Any]:
    statuses = [str(item.get("status")) for item in matrix]
    return {
        "repeat_count": repeat_count,
        "endpoint_count": len(matrix),
        "primary_count": statuses.count("primary"),
        "fallback_count": statuses.count("fallback"),
        "unstable_count": statuses.count("unstable"),
        "disabled_count": statuses.count("disabled"),
    }


def _markdown_report(report: dict[str, Any]) -> str:
    if report.get("version") == "market-data-live-probe-series-v1":
        return _markdown_series_report(report)
    lines = [
        "# Market Data Live Validation",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Scope: `{report['scope']}`",
        f"- Tushare token configured: `{report['environment']['tushare_token_configured']}`",
        f"- Secrets redacted: `{report['environment']['secrets_redacted']}`",
        f"- Python version: `{report['environment']['python_version']}`",
        f"- AkShare version: `{report['environment']['akshare_version']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    if report.get("capability_registry_summary"):
        lines.extend(_capability_registry_summary_markdown(report))
    if report.get("endpoint_status_matrix"):
        lines.extend(_status_matrix_markdown(report["endpoint_status_matrix"]))
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Provider | Endpoint | Capability | Available | Complete | Rows | Latency ms | Rate-limit risk | Anti-bot risk | Cost | Failure |",
            "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for check in report["checks"]:
        lines.append(
            "| {provider} | {endpoint} | {capability} | {availability} | {completeness} | {row_count} | {latency_ms} | {rate_limit_risk} | {anti_bot_risk} | {operational_cost} | {failure} |".format(
                provider=check["source"],
                endpoint=check["endpoint"],
                capability=check["capability"],
                availability=check["availability"],
                completeness=check["completeness"],
                row_count=check["row_count"],
                latency_ms=check["latency_ms"],
                rate_limit_risk=check["rate_limit_risk"],
                anti_bot_risk=check["anti_bot_risk"],
                operational_cost=check["operational_cost"],
                failure=_short_failure(check.get("failure_reason")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _markdown_series_report(report: dict[str, Any]) -> str:
    lines = [
        "# Market Data Live Validation Series",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Scope: `{report['scope']}`",
        f"- Repeat count: `{report['repeat_count']}`",
        f"- Interval seconds: `{report['interval_seconds']}`",
        f"- Tushare token configured: `{report['environment']['tushare_token_configured']}`",
        f"- Secrets redacted: `{report['environment']['secrets_redacted']}`",
        f"- Python version: `{report['environment']['python_version']}`",
        f"- AkShare version: `{report['environment']['akshare_version']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    if report.get("capability_registry_summary"):
        lines.extend(_capability_registry_summary_markdown(report))
    lines.extend(_status_matrix_markdown(report["endpoint_status_matrix"]))
    lines.append("")
    return "\n".join(lines)


def _status_matrix_markdown(matrix: list[dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "## Endpoint Status Matrix",
        "",
        "| Status | Configured | Gateway | Provider | Endpoint | Capability | Success | Latency ms | Max rows | Risks | Failure sample |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | --- |",
    ]
    for item in matrix:
        lines.append(
            "| {status} | {configured_status} | {gateway_mode} | {source} | {endpoint} | {capability} | {success_count}/{total_count} | {latency} | {max_row_count} | {risks} | {failure} |".format(
                status=item["status"],
                configured_status=item.get("configured_status") or "",
                gateway_mode=item.get("gateway_mode") or "",
                source=item["source"],
                endpoint=item["endpoint"],
                capability=item["capability"],
                success_count=item["success_count"],
                total_count=item["total_count"],
                latency=_latency_range(item),
                max_row_count=item["max_row_count"],
                risks=", ".join(item["anti_bot_risks"]),
                failure=item.get("failure_sample") or "",
            )
        )
    return lines


def _capability_registry_summary_markdown(report: dict[str, Any]) -> list[str]:
    summary = report["capability_registry_summary"]
    lines = [
        "",
        "## Capability Registry Summary",
        "",
        f"- Dataset count: `{summary['dataset_count']}`",
        f"- Analysis capability count: `{summary['analysis_capability_count']}`",
        f"- Missing or planned datasets: `{summary['missing_or_planned_datasets']}`",
    ]
    return lines


def _latency_range(item: dict[str, Any]) -> str:
    min_latency = item.get("min_latency_ms")
    max_latency = item.get("max_latency_ms")
    if min_latency is None or max_latency is None:
        return ""
    if min_latency == max_latency:
        return str(min_latency)
    return f"{min_latency}-{max_latency}"


def _short_failure(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).replace("|", "/")
    return text[:180] + ("..." if len(text) > 180 else "")


if __name__ == "__main__":
    raise SystemExit(main())
