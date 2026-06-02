from __future__ import annotations

import re
from datetime import UTC, datetime
from html import escape
from typing import Any, Protocol


class NewsBriefSource(Protocol):
    degradation_events: list[dict[str, Any]]

    def fetch_news_briefs(
        self,
        *,
        source_provider: str,
        src: str,
        start_datetime: str,
        end_datetime: str,
        limit: int,
    ) -> list[dict[str, Any]]: ...


def build_tushare_news_permission_smoke(
    *,
    source: NewsBriefSource,
    src_values: list[str],
    start_datetime: str,
    end_datetime: str,
    limit: int,
    source_provider: str = "tushare",
    generated_at: str | None = None,
) -> dict[str, Any]:
    environment_diagnostics = _environment_diagnostics(source)
    if environment_diagnostics == {
        "market_data_gateway_configured": False,
        "gateway_provider_loaded": False,
    }:
        src_results = [
            _gateway_not_configured_result(src)
            for src in src_values
        ]
    else:
        src_results = [
            _probe_src(
                source=source,
                source_provider=source_provider,
                src=src,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                limit=limit,
            )
            for src in src_values
        ]
    summary = _summary(src_results)
    return {
        "version": "tushare-news-permission-smoke-v1",
        "generated_at": generated_at or _utc_now(),
        "status": _overall_status(src_results),
        "input": {
            "source_provider": source_provider,
            "src_values": src_values,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "limit": limit,
        },
        "policy": {
            "uses_existing_auth_path_only": True,
            "new_auth_mechanism_created": False,
            "provider_access_boundary": "stock-data-gateway",
            "fni_integration_assignment_allowed": False,
        },
        "environment_diagnostics": environment_diagnostics,
        "summary": summary,
        "src_results": src_results,
        "degradation_events": _sanitize_degradation_events(
            getattr(source, "degradation_events", [])
        ),
    }


def render_tushare_news_permission_smoke_html(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>Tushare news 权限与 live smoke</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>Tushare news 权限与 live smoke</h1>",
            '<section class="summary">',
            _html_kv("总体状态", report.get("status")),
            _html_kv("src 数", summary.get("src_count", 0)),
            _html_kv("Dev-Ready", summary.get("dev_ready_count", 0)),
            _html_kv("Paid Permission Required", summary.get("paid_permission_required_count", 0)),
            _html_kv("Blocked", summary.get("blocked_count", 0)),
            _html_kv("No Data", summary.get("no_data_count", 0)),
            "<p>本检查只使用现有本地 env/token 与 Gateway news briefs 路径，不新增认证机制，不把 news integration 直接放进 FNI。</p>",
            "</section>",
            _results_table(_list(report.get("src_results"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _probe_src(
    *,
    source: NewsBriefSource,
    source_provider: str,
    src: str,
    start_datetime: str,
    end_datetime: str,
    limit: int,
) -> dict[str, Any]:
    try:
        rows = source.fetch_news_briefs(
            source_provider=source_provider,
            src=src,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            limit=limit,
        )
    except Exception as exc:
        reason = _sanitize_text(str(exc))
        return {
            "src": src,
            "status": _failure_status(reason),
            "row_count": 0,
            "sample_rows": [],
            "failure_reason": reason,
        }
    return {
        "src": src,
        "status": "Dev-Ready" if rows else "No Data",
        "row_count": len(rows),
        "sample_rows": [_safe_sample_row(row) for row in rows[:3]],
        "failure_reason": "",
    }


def _gateway_not_configured_result(src: str) -> dict[str, Any]:
    return {
        "src": src,
        "status": "Blocked",
        "row_count": 0,
        "sample_rows": [],
        "failure_reason": (
            "MARKET_DATA_GATEWAY_URL is not configured; gateway source boundary "
            "cannot be reached."
        ),
    }


def _environment_diagnostics(source: NewsBriefSource) -> dict[str, bool]:
    if not hasattr(source, "gateway_provider"):
        return {
            "market_data_gateway_configured": True,
            "gateway_provider_loaded": True,
        }
    gateway_provider = getattr(source, "gateway_provider", None)
    return {
        "market_data_gateway_configured": gateway_provider is not None,
        "gateway_provider_loaded": gateway_provider is not None,
    }


def _summary(src_results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "src_count": len(src_results),
        "dev_ready_count": _count_status(src_results, "Dev-Ready"),
        "paid_permission_required_count": _count_status(
            src_results,
            "Paid Permission Required",
        ),
        "blocked_count": _count_status(src_results, "Blocked"),
        "no_data_count": _count_status(src_results, "No Data"),
        "row_count": sum(int(result.get("row_count") or 0) for result in src_results),
    }


def _overall_status(src_results: list[dict[str, Any]]) -> str:
    statuses = {str(result.get("status") or "") for result in src_results}
    if "Dev-Ready" in statuses:
        return "Dev-Ready"
    if "Paid Permission Required" in statuses:
        return "Paid Permission Required"
    return "Blocked"


def _failure_status(reason: str) -> str:
    normalized = reason.casefold()
    if "permission" in normalized or "provider_permission_required" in normalized:
        return "Paid Permission Required"
    return "Blocked"


def _safe_sample_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "title": _sanitize_text(row.get("title")),
        "source": _sanitize_text(row.get("source")),
        "published_at": _sanitize_text(
            row.get("published_at") or row.get("datetime") or row.get("time")
        ),
    }


def _sanitize_degradation_events(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "capability": _sanitize_text(event.get("capability")),
            "reason": _sanitize_text(event.get("reason")),
        }
        for event in events
    ]


def _sanitize_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"(?i)(token|api[_-]?key|password|secret)=\S+", r"\1=***REDACTED***", text)
    return text


def _count_status(src_results: list[dict[str, Any]], status: str) -> int:
    return sum(1 for result in src_results if result.get("status") == status)


def _results_table(results: list[Any]) -> str:
    rows = [_mapping(result) for result in results]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("src", "状态", "Rows", "失败原因", "样例标题")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('src'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('row_count'))}</td>"
        f"<td>{_html_text(row.get('failure_reason'))}</td>"
        f"<td>{_html_text(_sample_titles(_list(row.get('sample_rows'))))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>src smoke 结果</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _sample_titles(rows: list[Any]) -> str:
    return "；".join(str(_mapping(row).get("title") or "") for row in rows)


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f7f8fa; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; font-size: 13px; }
th { background: #eef2f7; color: #323f4b; }
""".strip()
