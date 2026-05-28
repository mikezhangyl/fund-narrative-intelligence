from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_id(prefix: str, parts: list[Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(parts, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:10].upper()
    return f"{prefix}_{digest}"


def source_event_identity(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    explicit = _clean(event.get("event_id"))
    if explicit:
        return explicit, _metadata("explicit", ["event_id"])
    return stable_id(
        "EVT",
        [
            _clean(event.get("source_type")),
            _clean(event.get("event_time")),
            _clean(event.get("source_url")),
            _clean(event.get("title")),
            _clean(event.get("summary")),
        ],
    ), _metadata(
        "deterministic_fallback",
        ["source_type", "event_time", "source_url", "title", "summary"],
    )


def candidate_narrative_identity(candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key in ("candidate_narrative_id", "narrative_id"):
        explicit = _clean(candidate.get(key))
        if explicit:
            return explicit, _metadata("explicit", [key])
    return stable_id(
        "C_INTAKE",
        [
            _normalized_text(candidate.get("name") or candidate.get("narrative_name")),
            _normalized_text(candidate.get("canonical_taxonomy")),
        ],
    ), _metadata("deterministic_fallback", ["name", "canonical_taxonomy"])


def evidence_pack_identity(stock_code: Any, narrative_id: Any) -> tuple[str, dict[str, Any]]:
    return stable_id(
        "EPACK",
        [_normalized_code(stock_code), _normalized_code(narrative_id)],
    ), _metadata("deterministic_fallback", ["stock_code", "narrative_id"])


def candidate_mapping_identity(stock_code: Any, narrative_id: Any) -> tuple[str, dict[str, Any]]:
    return stable_id(
        "CMAP",
        [_normalized_code(stock_code), _normalized_code(narrative_id)],
    ), _metadata("deterministic_fallback", ["stock_code", "narrative_id"])


def review_action_identity(
    *,
    candidate_narrative_id: str,
    action: str,
    reviewed_by: str,
    review_note: str,
    reviewed_at: str,
    idempotency_key: str = "",
) -> tuple[str, dict[str, Any]]:
    if idempotency_key:
        return stable_id(
            "RA",
            [
                _clean(candidate_narrative_id),
                _clean(action),
                _clean(reviewed_by),
                _clean(idempotency_key),
            ],
        ), _metadata(
            "idempotency_key",
            ["candidate_narrative_id", "action", "reviewed_by", "idempotency_key"],
        )
    return stable_id(
        "RA",
        [
            _clean(candidate_narrative_id),
            _clean(action),
            _clean(reviewed_by),
            _clean(review_note),
            _clean(reviewed_at),
        ],
    ), _metadata(
        "append_event",
        ["candidate_narrative_id", "action", "reviewed_by", "review_note", "reviewed_at"],
    )


def promotion_decision_identity(
    *,
    candidate_narrative_id: str,
    target_narrative_id: str,
    review_action_id: str,
) -> tuple[str, dict[str, Any]]:
    return stable_id(
        "PD",
        [
            _clean(candidate_narrative_id),
            _clean(target_narrative_id),
            _clean(review_action_id),
        ],
    ), _metadata(
        "deterministic_fallback",
        ["candidate_narrative_id", "target_narrative_id", "review_action_id"],
    )


def _metadata(id_source: str, id_fields: list[str]) -> dict[str, Any]:
    return {"id_source": id_source, "id_fields": id_fields}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _normalized_text(value: Any) -> str:
    return _clean(value).casefold()


def _normalized_code(value: Any) -> str:
    return _clean(value).upper()
