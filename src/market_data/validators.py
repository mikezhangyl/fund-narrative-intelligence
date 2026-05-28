from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DataSourceValidationResult:
    source: str
    endpoint: str
    availability: bool
    latency_ms: float | None
    completeness: bool
    consistency: str
    schema_stability: bool
    rate_limit: str
    anti_bot_risk: str
    retry_recoverability: str
    operational_cost: str
    missing_fields: list[str] = field(default_factory=list)
    schema_fingerprint: str | None = None
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_records(
    *,
    source: str,
    endpoint: str,
    records: list[dict[str, Any]],
    required_fields: set[str],
    expected_schema_fingerprint: str | None = None,
    latency_ms: float | None = None,
    failure_reason: str | None = None,
) -> DataSourceValidationResult:
    observed_fields = {field for record in records for field in record}
    missing_fields = sorted(required_fields - observed_fields)
    fingerprint = schema_fingerprint(records)
    return DataSourceValidationResult(
        source=source,
        endpoint=endpoint,
        availability=failure_reason is None and bool(records),
        latency_ms=latency_ms,
        completeness=not missing_fields,
        consistency="not_evaluated",
        schema_stability=(
            expected_schema_fingerprint is None
            or expected_schema_fingerprint == fingerprint
        ),
        rate_limit="not_evaluated",
        anti_bot_risk="not_evaluated",
        retry_recoverability="not_evaluated",
        operational_cost="not_evaluated",
        missing_fields=missing_fields,
        schema_fingerprint=fingerprint,
        failure_reason=failure_reason,
    )


def schema_fingerprint(records: list[dict[str, Any]]) -> str:
    keys = sorted({key for record in records for key in record})
    return hashlib.sha256(",".join(keys).encode("utf-8")).hexdigest()


def compare_cross_source_counts(
    *,
    source_a: str,
    rows_a: list[dict[str, Any]],
    source_b: str,
    rows_b: list[dict[str, Any]],
    tolerance_ratio: float = 0.05,
) -> dict[str, Any]:
    max_count = max(len(rows_a), len(rows_b), 1)
    delta = abs(len(rows_a) - len(rows_b))
    return {
        "source_a": source_a,
        "source_b": source_b,
        "row_count_a": len(rows_a),
        "row_count_b": len(rows_b),
        "delta": delta,
        "within_tolerance": (delta / max_count) <= tolerance_ratio,
    }
