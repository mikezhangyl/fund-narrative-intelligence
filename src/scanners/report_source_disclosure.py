from __future__ import annotations

from typing import Any


def market_data_source_payload(
    *,
    data_source: Any,
    row_groups: list[list[dict[str, Any]]],
    failures: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    warnings = _dedupe_warnings(
        [
            *[_warning_from_event(event) for event in _degradation_events(data_source)],
            *[_warning_from_failure(failure) for failure in failures or []],
        ]
    )
    source_names = sorted(
        {
            str(row.get("source") or "")
            for rows in row_groups
            for row in rows
            if row.get("source")
        }
    )
    return {
        "source": _source_label(source_names),
        "provider": str(
            getattr(data_source, "provider_name", "")
            or data_source.__class__.__name__
        ),
        "data_fetch_mode": str(
            getattr(data_source, "data_fetch_mode", "") or "report_data_source"
        ),
        "source_names": source_names,
        "status": "degraded" if warnings else "available",
        "warning_count": len(warnings),
        "warnings": warnings,
        "degradation_events": _degradation_events(data_source),
        "fallback_count": sum(1 for warning in warnings if warning["type"] == "fallback"),
    }


def aggregate_market_data_sources(sources: list[dict[str, Any]]) -> dict[str, Any]:
    source_names = sorted(
        {
            str(name)
            for source in sources
            for name in _list(source.get("source_names"))
            if str(name)
        }
    )
    warnings = _dedupe_warnings(
        [
            dict(warning)
            for source in sources
            for warning in _list(source.get("warnings"))
            if isinstance(warning, dict)
        ]
    )
    providers = sorted(
        {str(source.get("provider") or "") for source in sources if source.get("provider")}
    )
    return {
        "source": _source_label(source_names),
        "provider": ", ".join(providers),
        "data_fetch_mode": "aggregated_report_sources",
        "source_names": source_names,
        "status": "degraded" if warnings else "available",
        "warning_count": len(warnings),
        "warnings": warnings,
        "degradation_events": warnings,
        "fallback_count": sum(1 for warning in warnings if warning["type"] == "fallback"),
    }


def source_status_zh(source: dict[str, Any]) -> str:
    status = str(source.get("status") or "")
    diagnostics = _mapping(source.get("diagnostics"))
    status_summary = _mapping(diagnostics.get("status_summary"))
    if not status:
        status = str(status_summary.get("status") or "")
    warning_count = int(source.get("warning_count") or 0)
    if status in {"degraded", "partial", "available_with_data_gaps"} or warning_count:
        return "有告警或降级"
    return "无告警"


def source_fallback_zh(source: dict[str, Any]) -> str:
    diagnostics = _mapping(source.get("diagnostics"))
    provider_source = _mapping(diagnostics.get("provider_source"))
    fallback = (
        source.get("fallback_source")
        or provider_source.get("fallback_source")
        or source.get("fallback_provider")
        or ""
    )
    fallback_count = int(source.get("fallback_count") or 0)
    if fallback:
        return str(fallback)
    if fallback_count:
        return f"{fallback_count} 条回退告警"
    return "无"


def source_warning_summary_zh(source: dict[str, Any]) -> str:
    warnings = [
        _warning_label(warning)
        for warning in _list(source.get("warnings"))
        if isinstance(warning, dict)
    ]
    if warnings:
        return "；".join(warnings)
    return "无告警"


def _warning_from_event(event: dict[str, Any]) -> dict[str, str]:
    return {
        "type": _warning_type(event),
        "code": str(event.get("type") or event.get("capability") or "DEGRADED"),
        "capability": str(event.get("capability") or ""),
        "message": str(event.get("reason") or event.get("message") or event),
    }


def _warning_from_failure(failure: dict[str, str]) -> dict[str, str]:
    return {
        "type": "failure",
        "code": str(failure.get("capability") or "FAILURE"),
        "capability": str(failure.get("capability") or ""),
        "message": str(failure.get("reason") or failure),
    }


def _warning_type(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "")
    if "fallback" in event_type or event.get("fallback_provider"):
        return "fallback"
    return "degradation"


def _warning_label(warning: dict[str, Any]) -> str:
    code = str(warning.get("code") or warning.get("capability") or "WARNING")
    message = str(warning.get("message") or warning.get("reason") or "")
    return f"{code}: {message}" if message else code


def _dedupe_warnings(warnings: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for warning in warnings:
        key = (
            str(warning.get("code") or ""),
            str(warning.get("capability") or ""),
            str(warning.get("message") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped


def _degradation_events(data_source: Any) -> list[dict[str, Any]]:
    events = getattr(data_source, "degradation_events", [])
    return [dict(event) for event in events if isinstance(event, dict)]


def _source_label(source_names: list[str]) -> str:
    if not source_names:
        return "unspecified"
    if len(source_names) == 1:
        return source_names[0]
    return "mixed"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
