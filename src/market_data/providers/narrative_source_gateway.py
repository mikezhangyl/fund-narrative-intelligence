from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from src import local_env
from src.market_data.providers.local_gateway import (
    DEFAULT_GATEWAY_BASE_URL_ENV,
    DEFAULT_GATEWAY_TIMEOUT_SECONDS_ENV,
)
from src.scanners.source_event_schema import validate_source_event

GatewayHttpFetcher = Callable[
    [str, str, dict[str, Any] | None, float],
    tuple[int, dict[str, Any]],
]

UNIFIED_SOURCE_EVENTS_PATH = "/api/v1/market-data/narrative/source-events"
SOURCE_KINDS = (
    "official_filings",
    "official_disclosures",
    "official_sources",
    "news_context",
    "open_news_index",
    "industry_media",
    "social_heat",
)
SOURCE_KIND_PATHS = {source_kind: UNIFIED_SOURCE_EVENTS_PATH for source_kind in SOURCE_KINDS}
LEGACY_SOURCE_KIND_PATHS = {
    "official_filings": "/api/v1/market-data/narrative/source-events/official-filings",
    "official_disclosures": "/api/v1/market-data/narrative/source-events/official-disclosures",
    "news_context": "/api/v1/market-data/narrative/source-events/news-context",
    "social_heat": "/api/v1/market-data/narrative/source-events/social-heat",
}

REQUIRED_GATEWAY_SOURCE_EVENT_FIELDS = (
    "source_event_id",
    "source_type",
    "source_provider",
    "source_url",
    "title",
    "event_time",
    "fetched_at",
    "trust_tier",
    "source_quality",
    "license_scope",
    "retention_policy",
    "metadata_only",
    "degradation_events",
)


class GatewaySourceUnavailableError(RuntimeError):
    pass


class NarrativeSourceGatewayClient:
    provider_name = "local-market-data-gateway-narrative-source"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        fetcher: GatewayHttpFetcher | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.fetcher = fetcher or _http_fetch

    @classmethod
    def from_env(cls) -> "NarrativeSourceGatewayClient | None":
        base_url = local_env.get_config_value(DEFAULT_GATEWAY_BASE_URL_ENV)
        if not base_url:
            return None
        return cls(
            base_url=base_url,
            timeout_seconds=_float_config(DEFAULT_GATEWAY_TIMEOUT_SECONDS_ENV, 10.0),
        )

    def fetch_source_events(
        self,
        *,
        source_kind: str,
        symbols: list[str] | None = None,
        query: str | None = None,
        limit: int = 10,
        source_provider: str | None = None,
        entity_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        trust_tier: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        if source_kind not in SOURCE_KIND_PATHS:
            raise ValueError(f"unsupported narrative source kind: {source_kind}")
        request_query = _request_query(
            source_kind=source_kind,
            symbols=symbols,
            query=query,
            limit=limit,
            source_provider=source_provider,
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time,
            trust_tier=trust_tier,
            cursor=cursor,
        )
        status, payload = self.fetcher(
            "GET",
            _url_with_query(
                urljoin(
                    self.base_url.rstrip("/") + "/",
                    UNIFIED_SOURCE_EVENTS_PATH.lstrip("/"),
                ),
                request_query,
            ),
            None,
            self.timeout_seconds,
        )
        if status < 200 or status >= 300:
            raise GatewaySourceUnavailableError(
                _gateway_source_error_message(status=status, payload=payload)
            )
        rows = _rows_from_payload(payload)
        normalized_rows = [normalize_gateway_source_event(row) for row in rows]
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        degradation_events = _result_degradation_events(normalized_rows, meta=meta)
        return {
            "source_kind": source_kind,
            "status": _result_status(normalized_rows, meta=meta),
            "row_count": len(normalized_rows),
            "rows": normalized_rows,
            "meta": meta,
            "degradation_events": degradation_events,
        }


def normalize_gateway_source_event(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("gateway source event row must be an object")
    missing = [
        field
        for field in REQUIRED_GATEWAY_SOURCE_EVENT_FIELDS
        if field not in row or row[field] in ("", None)
    ]
    if missing:
        raise ValueError(f"gateway source event missing required fields: {', '.join(missing)}")
    degradation_events = row.get("degradation_events")
    if not isinstance(degradation_events, list):
        raise ValueError("gateway source event degradation_events must be a list")
    normalized = validate_source_event(
        {
            "event_id": str(row["source_event_id"]),
            "source_type": _v1_source_type(row),
            "provider": f"gateway_{row['source_provider']}",
            "source_url": str(row["source_url"]),
            "event_time": str(row["event_time"]),
            "title": str(row["title"]),
            "summary": str(row.get("summary") or ""),
            "stock_codes": _strings(row.get("stock_codes")),
            "narrative_hints": _strings(row.get("narrative_hints")),
            "evidence_claims": _strings(row.get("evidence_claims")),
            "source_metadata": {
                "provider": f"gateway_{row['source_provider']}",
                "upstream_provider": str(row["source_provider"]),
                "source_mode": "normalized_gateway",
                "fetched_at": str(row["fetched_at"]),
                "license_scope": str(row["license_scope"]),
                "retention_policy": str(row["retention_policy"]),
                "metadata_only": bool(row["metadata_only"]),
                "degradation_events": degradation_events,
            },
        }
    )
    return {
        **normalized,
        "source_event_id": str(row["source_event_id"]),
        "source_provider": str(row["source_provider"]),
        "fetched_at": str(row["fetched_at"]),
        "trust_tier": str(row["trust_tier"]),
        "source_quality": str(row["source_quality"]),
        "license_scope": str(row["license_scope"]),
        "retention_policy": str(row["retention_policy"]),
        "metadata_only": bool(row["metadata_only"]),
        "degradation_events": degradation_events,
        "provider_metadata": row.get("provider_metadata") or {},
        "source_document_id": str(row.get("source_document_id") or ""),
        "source_document_title": str(row.get("source_document_title") or ""),
        "source_document_url": str(row.get("source_document_url") or ""),
        "excerpt": str(row.get("excerpt") or ""),
    }


def _request_query(
    *,
    source_kind: str,
    symbols: list[str] | None,
    query: str | None,
    limit: int,
    source_provider: str | None = None,
    entity_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    trust_tier: str | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"source_kind": source_kind, "limit": max(1, int(limit))}
    if symbols is not None:
        body = {**body, "symbol": ",".join(str(symbol) for symbol in symbols if str(symbol))}
    if query is not None:
        body = {**body, "keyword": query}
    optional = {
        "source_provider": source_provider,
        "entity_id": entity_id,
        "start_time": start_time,
        "end_time": end_time,
        "trust_tier": trust_tier,
        "cursor": cursor,
    }
    body = {**body, **{key: value for key, value in optional.items() if value}}
    return body


def _url_with_query(url: str, query: dict[str, Any]) -> str:
    return f"{url}?{urlencode(query)}"


def _rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise GatewaySourceUnavailableError("gateway narrative source response missing data object")
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise GatewaySourceUnavailableError("gateway narrative source response missing data.rows")
    if not all(isinstance(row, dict) for row in rows):
        raise GatewaySourceUnavailableError("gateway narrative source rows must be objects")
    return list(rows)


def _result_status(rows: list[dict[str, Any]], *, meta: dict[str, Any]) -> str:
    if str(meta.get("status") or "").casefold() == "degraded":
        return "degraded"
    return "completed" if rows else "missing"


def _result_degradation_events(
    rows: list[dict[str, Any]], *, meta: dict[str, Any]
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    meta_events = meta.get("degradation_events")
    if isinstance(meta_events, list):
        events.extend(event for event in meta_events if isinstance(event, dict))
    warning = meta.get("warning")
    if isinstance(warning, dict):
        events.append(warning)
    for row in rows:
        row_events = row.get("degradation_events")
        if isinstance(row_events, list):
            events.extend(event for event in row_events if isinstance(event, dict))
    return events


def _v1_source_type(row: dict[str, Any]) -> str:
    source_type = str(row["source_type"])
    if source_type in {"news", "announcement", "filing", "manual", "social", "social_future"}:
        return source_type
    provider_metadata = row.get("provider_metadata")
    source_kind = (
        str(provider_metadata.get("source_kind") or "")
        if isinstance(provider_metadata, dict)
        else ""
    )
    if source_type in {"official", "public_official"} or source_kind == "official_sources":
        return "announcement"
    if source_type in {"public_industry_media", "industry_media"} or source_kind == "industry_media":
        return "news"
    return source_type


def _gateway_source_error_message(*, status: int, payload: dict[str, Any]) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        code = str(error.get("code") or "UNKNOWN_GATEWAY_ERROR")
        message = str(error.get("message") or "")
        return (
            "gateway narrative source route unavailable: "
            f"HTTP {status}: {code}: {message}"
        )
    return f"gateway narrative source route unavailable: HTTP {status}"


def _http_fetch(
    method: str,
    url: str,
    json_body: dict[str, Any] | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    method_name = method.upper()
    body = None if method_name == "GET" else json.dumps(json_body or {}).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        url,
        data=body,
        headers=headers,
        method=method_name,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"code": "http_error", "message": str(exc)}}
        return int(exc.code), payload
    except (OSError, URLError) as exc:
        raise GatewaySourceUnavailableError(
            f"gateway narrative source route unavailable: {exc}"
        ) from exc


def _float_config(name: str, default: float) -> float:
    value = local_env.get_config_value(name)
    if value is None:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        return default


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
