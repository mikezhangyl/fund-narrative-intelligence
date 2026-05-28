from __future__ import annotations

from typing import Any

from stock_narrative_service.config import ServiceConfig

DIAGNOSTICS_SCHEMA_VERSION = "narrative-operational-diagnostics-v1"
DATA_FETCH_MODE = "json_file_ledgers_v1"
FALLBACK_SOURCE = "local_prototype"


def warning_payload(
    *,
    code: str,
    message: str,
    classification: str,
    scope: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "classification": classification,
    }
    if scope:
        payload["scope"] = scope
    return payload


def operational_diagnostics(
    *,
    config: ServiceConfig,
    status: str,
    warnings: list[dict[str, Any]] | None = None,
    queue_summary: dict[str, int] | None = None,
    audit_status: str = "",
    product_data_gaps: list[dict[str, Any]] | None = None,
    system_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    warnings = list(warnings or [])
    product_data_gaps = list(product_data_gaps or _warnings_by_classification(
        warnings,
        "product_data_gap",
    ))
    system_failures = list(system_failures or _warnings_by_classification(
        warnings,
        "system_failure",
    ))
    summary_status = status
    if status == "available" and product_data_gaps:
        summary_status = "available_with_data_gaps"
    return {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "provider_source": {
            "source": "narrative_service",
            "provider": config.provider_name,
            "provider_version": config.provider_version,
            "data_fetch_mode": DATA_FETCH_MODE,
            "fallback_source": FALLBACK_SOURCE,
        },
        "status_summary": {
            "status": summary_status,
            "warning_count": len(warnings),
            "product_data_gap_count": len(product_data_gaps),
            "system_failure_count": len(system_failures),
        },
        "queue_summary": dict(queue_summary or {}),
        "audit_status": audit_status,
        "product_data_gaps": product_data_gaps,
        "system_failures": system_failures,
    }


def _warnings_by_classification(
    warnings: list[dict[str, Any]],
    classification: str,
) -> list[dict[str, Any]]:
    return [
        {
            "code": str(item.get("code") or ""),
            "message": str(item.get("message") or ""),
            **({"scope": str(item["scope"])} if item.get("scope") else {}),
        }
        for item in warnings
        if item.get("classification") == classification
    ]
