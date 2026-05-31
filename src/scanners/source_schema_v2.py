from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.scanners.source_event_schema import validate_source_event

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_V2_PATH = PROJECT_ROOT / "config" / "narrative_source_schema_v2.json"


def load_source_schema_v2(path: Path = DEFAULT_SCHEMA_V2_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source_event_v2(
    event: dict[str, Any],
    *,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_schema = schema or load_source_schema_v2()
    required = _strings(active_schema["entities"]["SourceEvent"]["required_fields"])
    missing = [
        field
        for field in required
        if field not in event or event[field] in ("", None)
    ]
    if missing:
        raise ValueError(f"SourceEvent v2 missing required fields: {', '.join(missing)}")
    source_class = str(event["source_class"])
    if source_class not in set(_strings(active_schema.get("supported_source_classes"))):
        raise ValueError(f"unsupported SourceEvent source_class: {source_class}")
    raw_policy = _mapping(event.get("raw_content_policy"))
    raw_policy_missing = [
        field
        for field in _strings(
            _mapping(active_schema.get("raw_content_policy_contract")).get(
                "required_fields"
            )
        )
        if field not in raw_policy
    ]
    if raw_policy_missing:
        raise ValueError(
            "SourceEvent v2 raw_content_policy missing required fields: "
            + ", ".join(raw_policy_missing)
        )
    confidence = _confidence(event.get("confidence"))
    normalized = {
        **deepcopy(event),
        "schema_version": active_schema["version"],
        "confidence": confidence,
        "metadata_only": bool(event.get("metadata_only", False)),
        "raw_content_policy": {
            **raw_policy,
            "raw_retention_allowed": bool(raw_policy.get("raw_retention_allowed")),
            "excerpt_retention_allowed": bool(
                raw_policy.get("excerpt_retention_allowed")
            ),
        },
        "source_quality": _source_quality(event, confidence=confidence),
        "trust_status": _mapping(active_schema.get("trust_policy")).get(
            "default_trust_status",
            "candidate_untrusted",
        ),
        "promotion_effect": _mapping(active_schema.get("trust_policy")).get(
            "promotion_effect",
            "none",
        ),
        "direct_crawling_allowed": False,
        "validated_at": _utc_now(),
    }
    return normalized


def source_event_v2_to_v1(event: dict[str, Any]) -> dict[str, Any]:
    schema = load_source_schema_v2()
    normalized = validate_source_event_v2(event, schema=schema)
    v1_type = _mapping(schema.get("source_class_to_v1_source_type")).get(
        normalized["source_class"],
        "manual",
    )
    if normalized["source_class"] == "official_disclosure" and normalized["event_type"] != "filing":
        v1_type = "announcement"
    v1_event = validate_source_event(
        {
            "event_id": normalized["source_event_id"],
            "source_type": v1_type,
            "provider": normalized["provider"],
            "source_url": normalized["source_url"],
            "event_time": normalized["published_at"],
            "title": normalized["title"],
            "summary": normalized["text_excerpt"],
            "stock_codes": _stock_codes(normalized),
            "narrative_hints": _strings(normalized.get("topics")),
            "evidence_claims": _strings(normalized.get("evidence_ids")),
            "source_metadata": {
                "provider": normalized["provider"],
                "schema_version": normalized["schema_version"],
                "source_id": normalized["source_id"],
                "source_event_id": normalized["source_event_id"],
                "fetched_at": normalized["fetched_at"],
                "license_scope": normalized["license_scope"],
                "retention_policy": normalized["retention_policy"],
                "raw_hash": normalized["raw_hash"],
                "source_trust_tier": normalized["source_trust_tier"],
                "freshness_bucket": normalized["freshness_bucket"],
                "raw_content_policy": normalized["raw_content_policy"],
            },
        }
    )
    return {
        **v1_event,
        "trust_status": normalized["trust_status"],
        "promotion_effect": normalized["promotion_effect"],
        "direct_crawling_allowed": False,
    }


def build_source_schema_v2_report(
    *,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_schema = schema or load_source_schema_v2()
    entities = active_schema.get("entities") if isinstance(active_schema.get("entities"), dict) else {}
    return {
        "version": "source-schema-v2-report-v1",
        "schema_version": str(active_schema.get("version") or ""),
        "generated_at": _utc_now(),
        "summary": {
            "entity_count": len(entities),
            "source_class_count": len(_strings(active_schema.get("supported_source_classes"))),
        },
        "supported_source_classes": _strings(active_schema.get("supported_source_classes")),
        "entities": entities,
        "raw_content_policy_contract": _mapping(
            active_schema.get("raw_content_policy_contract")
        ),
        "trust_policy": _mapping(active_schema.get("trust_policy")),
    }


def _source_quality(event: dict[str, Any], *, confidence: float) -> dict[str, Any]:
    return {
        "source_quality_id": str(event.get("source_quality_id") or ""),
        "source_event_id": str(event["source_event_id"]),
        "source_trust_tier": str(event["source_trust_tier"]),
        "source_quality": str(event.get("source_quality") or event["source_trust_tier"]),
        "license_scope": str(event["license_scope"]),
        "retention_policy": str(event["retention_policy"]),
        "metadata_only": bool(event.get("metadata_only", False)),
        "freshness_bucket": str(event["freshness_bucket"]),
        "confidence": confidence,
        "degradation_events": _list(event.get("degradation_events")),
    }


def _stock_codes(event: dict[str, Any]) -> list[str]:
    codes = []
    for entity in _list(event.get("entities")):
        if str(entity.get("entity_type") or "") in {"ticker", "stock_code"}:
            codes.append(str(entity.get("value") or ""))
    return [code for code in codes if code]


def _confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("SourceEvent v2 confidence must be numeric") from exc
    if numeric < 0.0 or numeric > 1.0:
        raise ValueError("SourceEvent v2 confidence must be between 0 and 1")
    return numeric


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
