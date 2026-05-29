from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "config" / "source_event_schema.json"
SCHEMA_VERSION = "source-event-schema-v1"


def load_source_event_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_source_event(event)
    if not normalized["source_type"]:
        raise ValueError("source event source_type must be non-empty")
    if not normalized["title"]:
        raise ValueError("source event title must be non-empty")
    return normalized


def normalize_source_event(event: dict[str, Any]) -> dict[str, Any]:
    schema = load_source_event_schema()
    raw_type = str(event.get("source_type") or "manual")
    source_type = _source_type(raw_type, schema=schema)
    provider = _provider(event)
    stock_codes = _stock_codes(event)
    narrative_hints = _strings(event.get("narrative_hints")) or _strings(
        event.get("keywords")
    )
    normalized = {
        **deepcopy(event),
        "schema_version": SCHEMA_VERSION,
        "event_id": str(event.get("event_id") or ""),
        "source_type": source_type,
        "provider": provider,
        "source_url": str(event.get("source_url") or ""),
        "event_time": str(event.get("event_time") or ""),
        "title": str(event.get("title") or ""),
        "summary": str(event.get("summary") or ""),
        "stock_codes": stock_codes,
        "narrative_hints": narrative_hints,
        "evidence_claims": _strings(event.get("evidence_claims")),
        "mentioned_stocks": _mentioned_stocks(event, stock_codes=stock_codes),
        "keywords": narrative_hints,
        "source_metadata": _source_metadata(
            event,
            source_type=source_type,
            provider=provider,
            schema=schema,
        ),
        "quality_gaps": _quality_gaps(
            source_url=str(event.get("source_url") or ""),
            event_time=str(event.get("event_time") or ""),
            stock_codes=stock_codes,
        ),
        "trust_status": "candidate_untrusted",
        "promotion_effect": "none",
        "external_access_policy": "gateway_change_request_first",
        "direct_crawling_allowed": False,
    }
    event_id = normalized["event_id"] or _stable_id(
        "EVT",
        [
            normalized["source_type"],
            normalized["provider"],
            normalized["source_url"],
            normalized["event_time"],
            normalized["title"],
        ],
    )
    normalized["event_id"] = event_id
    normalized["dedupe_key"] = source_event_dedupe_key(normalized)
    return normalized


def source_event_dedupe_key(event: dict[str, Any]) -> str:
    values = [
        event.get("source_type"),
        event.get("provider"),
        event.get("source_url"),
        event.get("event_time"),
        event.get("title"),
        ",".join(_strings(event.get("stock_codes"))),
    ]
    return _stable_id("SEVT", values)


def _source_type(value: str, *, schema: dict[str, Any]) -> str:
    aliases = schema.get("source_type_aliases")
    if isinstance(aliases, dict) and value in aliases:
        return str(aliases[value])
    supported = schema.get("supported_source_types")
    if isinstance(supported, list) and value in supported:
        return value
    return "manual"


def _provider(event: dict[str, Any]) -> str:
    metadata = event.get("source_metadata")
    if isinstance(metadata, dict) and metadata.get("provider"):
        return str(metadata["provider"])
    return str(event.get("provider") or event.get("source_name") or "")


def _source_metadata(
    event: dict[str, Any],
    *,
    source_type: str,
    provider: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    metadata = event.get("source_metadata")
    raw = dict(metadata) if isinstance(metadata, dict) else {}
    preferences = _mapping(schema.get("provider_preferences"))
    return {
        "provider": provider,
        "provider_version": str(
            raw.get("provider_version") or event.get("provider_version") or ""
        ),
        "permission_status": str(
            raw.get("permission_status")
            or event.get("permission_status")
            or "unspecified"
        ),
        "degradation_state": str(
            raw.get("degradation_state")
            or event.get("degradation_state")
            or "unknown"
        ),
        "provider_preference": _strings(preferences.get(source_type)),
        "source_mode": str(
            raw.get("source_mode") or event.get("source_mode") or _source_mode(provider)
        ),
    }


def _source_mode(provider: str) -> str:
    if provider.startswith("gateway_"):
        return "normalized_gateway"
    if provider.startswith("manual") or provider.endswith("fixture"):
        return "local_fixture"
    return "external_contract"


def _quality_gaps(
    *,
    source_url: str,
    event_time: str,
    stock_codes: list[str],
) -> list[str]:
    gaps = []
    if not source_url:
        gaps.append("missing_source_url")
    if not event_time:
        gaps.append("missing_event_time")
    if not stock_codes:
        gaps.append("missing_stock_codes")
    return gaps


def _stock_codes(event: dict[str, Any]) -> list[str]:
    explicit = _strings(event.get("stock_codes"))
    if explicit:
        return explicit
    return [
        str(item.get("stock_code") or "")
        for item in _list(event.get("mentioned_stocks"))
        if item.get("stock_code")
    ]


def _mentioned_stocks(
    event: dict[str, Any],
    *,
    stock_codes: list[str],
) -> list[dict[str, str]]:
    stocks = _list(event.get("mentioned_stocks"))
    if stocks:
        return [
            {
                "stock_code": str(item.get("stock_code") or ""),
                "stock_name": str(item.get("stock_name") or ""),
            }
            for item in stocks
        ]
    return [{"stock_code": stock_code, "stock_name": ""} for stock_code in stock_codes]


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1(
        "|".join(str(value or "") for value in values).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16].upper()}"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
