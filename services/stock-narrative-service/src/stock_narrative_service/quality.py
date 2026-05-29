from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from html import escape
from typing import Any

QUALITY_CONTRACT_VERSION = "narrative-quality-contract-v1"
QUALITY_SCORECARD_VERSION = "narrative-quality-scorecards-v1"
EXTRACTION_REVIEW_VERSION = "narrative-extraction-quality-review-v1"
QUALITY_AUDIT_VERSION = "narrative-quality-audit-v1"
QUALITY_FORMULA_VERSION = "evidence-quality-deterministic-v1"
REQUIRED_ENTITY_FIELDS = ("tickers", "sectors", "concepts", "keywords")
SECRET_KEY_FRAGMENTS = ("secret", "token", "key", "password", "credential")


def quality_contract() -> dict[str, Any]:
    return {
        "version": QUALITY_CONTRACT_VERSION,
        "ownership": {
            "quality_owner": "narrative_service",
            "provider_owner": "gateway",
            "consumer_role": "fni_consumes_quality_metadata_only",
        },
        "required_sections": [
            "quality_score",
            "source_lineage",
            "source_diversity",
            "recency_staleness",
            "extraction_confidence",
            "provider_reliability",
            "contradiction_status",
            "warnings",
        ],
        "endpoints": {
            "contract": "/api/v1/narratives/quality/contract",
            "scorecards": "/api/v1/narratives/quality/scorecards",
            "extractions": "/api/v1/narratives/quality/extractions",
            "audit": "/api/v1/narratives/quality/audit",
            "workspace": "/narratives/quality",
        },
        "formula_version": QUALITY_FORMULA_VERSION,
        "ai_policy": {
            "score_override_allowed": False,
            "trust_promotion_allowed": False,
            "role": "explanation_only",
        },
        "consumer_policy": {
            "fni_recomputes_quality": False,
            "quality_authority": "narrative_service",
        },
    }


def quality_scorecards(
    events: list[dict[str, Any]],
    *,
    evidence_packs: dict[str, Any] | None = None,
    as_of: str = "",
    freshness_window_days: Any = "",
) -> dict[str, Any]:
    scoring_as_of = _parse_datetime(as_of) or _latest_event_time(events) or _now()
    freshness_window = _positive_int(freshness_window_days, default=30)
    grouped = _events_by_candidate(events)
    cards = [
        _score_candidate_events(
            narrative_id=candidate_id,
            rows=rows,
            as_of=scoring_as_of,
            freshness_window_days=freshness_window,
        )
        for candidate_id, rows in grouped.items()
    ]
    return {
        "version": QUALITY_SCORECARD_VERSION,
        "formula_version": QUALITY_FORMULA_VERSION,
        "scoring_config": {
            "as_of": scoring_as_of.isoformat(),
            "freshness_window_days": freshness_window,
        },
        "scorecards": sorted(
            cards,
            key=lambda item: (
                -float(item.get("quality_score") or 0),
                str(item.get("narrative_id") or ""),
            ),
        ),
        "evidence_pack_scorecards": evidence_pack_scorecards(evidence_packs or {}),
        "historical_retention": (
            "stale and contradicted records remain auditable and are not deleted"
        ),
    }


def evidence_pack_scorecards(evidence_packs: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for pack in _list(evidence_packs.get("packs")):
        stock_code = str(pack.get("stock_code") or "")
        for mapping in _list(pack.get("proposed_mappings")):
            evidence_items = _list(mapping.get("evidence_items"))
            confidence = _mapping(mapping.get("confidence_components"))
            base_score = _float(confidence.get("evidence_quality")) * 100
            if not base_score:
                base_score = min(100.0, 45.0 + len(evidence_items) * 20.0)
            issue_codes = []
            if not evidence_items:
                issue_codes.append("MISSING_EVIDENCE_ITEMS")
                base_score = min(base_score, 35.0)
            if not str(mapping.get("mapping_rationale") or "").strip():
                issue_codes.append("MISSING_MAPPING_RATIONALE")
                base_score = min(base_score, 70.0)
            if not _strings(mapping.get("exclusion_rationale")):
                issue_codes.append("MISSING_EXCLUSION_RATIONALE")
                base_score = min(base_score, 70.0)
            score = round(max(0.0, min(100.0, base_score)), 1)
            cards.append(
                {
                    "evidence_pack_id": str(mapping.get("evidence_pack_id") or ""),
                    "candidate_mapping_id": str(mapping.get("candidate_mapping_id") or ""),
                    "lookup": {
                        "stock_code": stock_code,
                        "narrative_id": str(mapping.get("narrative_id") or ""),
                    },
                    "narrative_name": str(mapping.get("narrative_name") or ""),
                    "quality_score": score,
                    "quality_grade": _grade(score),
                    "issue_codes": issue_codes,
                    "evidence_item_count": len(evidence_items),
                    "source_lineage": [
                        _evidence_item_lineage(item) for item in evidence_items
                    ],
                    "formula_version": QUALITY_FORMULA_VERSION,
                    "promotion_effect": "none",
                }
            )
    return sorted(
        cards,
        key=lambda item: (
            str(_mapping(item.get("lookup")).get("stock_code") or ""),
            str(_mapping(item.get("lookup")).get("narrative_id") or ""),
        ),
    )


def extraction_quality_review(events: list[dict[str, Any]]) -> dict[str, Any]:
    items = [_extraction_item(event) for event in events]
    summary = Counter(str(item.get("review_status") or "") for item in items)
    return {
        "version": EXTRACTION_REVIEW_VERSION,
        "formula_version": QUALITY_FORMULA_VERSION,
        "summary": {
            "pass": int(summary.get("pass", 0)),
            "needs_review": int(summary.get("needs_review", 0)),
        },
        "items": sorted(
            items,
            key=lambda item: str(item.get("source_event_id") or ""),
        ),
    }


def quality_audit(
    events: list[dict[str, Any]],
    *,
    evidence_packs: dict[str, Any] | None = None,
    as_of: str = "",
    freshness_window_days: Any = "",
) -> dict[str, Any]:
    score_payload = quality_scorecards(
        events,
        evidence_packs=evidence_packs,
        as_of=as_of,
        freshness_window_days=freshness_window_days,
    )
    extraction_payload = extraction_quality_review(events)
    cards = _list(score_payload.get("scorecards"))
    issue_counts = Counter(
        issue
        for card in cards
        for issue in _strings(card.get("issue_codes"))
    )
    issues = [
        {
            "narrative_id": str(card.get("narrative_id") or ""),
            "narrative_name": str(card.get("narrative_name") or ""),
            "issue_code": issue,
            "quality_score": float(card.get("quality_score") or 0),
            "evidence_refs": _strings(card.get("evidence_refs")),
            "source_event_ids": [
                str(item.get("source_event_id") or "")
                for item in _list(card.get("source_lineage"))
            ],
        }
        for card in cards
        for issue in _strings(card.get("issue_codes"))
    ]
    return {
        "version": QUALITY_AUDIT_VERSION,
        "formula_version": QUALITY_FORMULA_VERSION,
        "generated_at": _now().isoformat(),
        "summary": {
            "narrative_count": len(cards),
            "source_event_count": len(events),
            "issue_count": len(issues),
            "needs_review_extraction_count": extraction_payload["summary"][
                "needs_review"
            ],
        },
        "issue_summary": dict(sorted(issue_counts.items())),
        "source_provider_summary": _source_provider_summary(events),
        "extraction_confidence_issues": [
            item
            for item in _list(extraction_payload.get("items"))
            if str(item.get("review_status") or "") == "needs_review"
        ],
        "issues": issues,
        "scorecards": cards,
        "evidence_pack_scorecards": _list(score_payload.get("evidence_pack_scorecards")),
        "export_manifest": {
            "schema_version": QUALITY_AUDIT_VERSION,
            "formula_version": QUALITY_FORMULA_VERSION,
            "source_endpoint": "/api/v1/narratives/quality/audit",
            "human_workspace": "/narratives/quality",
        },
        "consumer_policy": quality_contract()["consumer_policy"],
    }


def render_quality_audit_html(audit: dict[str, Any]) -> str:
    summary = _mapping(audit.get("summary"))
    issue_summary = _mapping(audit.get("issue_summary"))
    rows = "\n".join(_render_scorecard_row(item) for item in _list(audit.get("scorecards")))
    if not rows:
        rows = '<tr><td colspan="6">暂无叙事质量记录。</td></tr>'
    issue_items = "\n".join(
        f"<li><code>{_html(code)}</code>: {_html(count)}</li>"
        for code, count in issue_summary.items()
    )
    if not issue_items:
        issue_items = "<li>暂无质量问题。</li>"
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>叙事质量审计工作台</title>",
            "<style>",
            "body{margin:0;background:#f5f7fa;color:#17212b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}",
            "main{max-width:1180px;margin:0 auto;padding:24px}",
            "header{border-bottom:1px solid #d8e0e8;padding-bottom:16px}",
            "h1{font-size:28px;margin:0 0 8px}",
            "p{margin:0;color:#5a6878}",
            ".summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}",
            ".metric{background:#fff;border:1px solid #d8e0e8;padding:12px}",
            ".metric strong{display:block;font-size:22px}",
            "table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d8e0e8}",
            "th,td{text-align:left;border-bottom:1px solid #e5ebf1;padding:10px;vertical-align:top}",
            "th{font-size:12px;color:#596779;background:#eef3f7}",
            "code{background:#eef3f7;padding:2px 5px}",
            ".issues{background:#fff;border:1px solid #d8e0e8;margin:18px 0;padding:14px}",
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            "<header>",
            "<h1>叙事质量审计工作台</h1>",
            "<p>用于审阅证据质量、来源可靠性、抽取置信度、陈旧叙事和矛盾信号；质量分由 Narrative Service 计算。</p>",
            "</header>",
            '<section class="summary">',
            _metric("叙事数", summary.get("narrative_count")),
            _metric("质量问题", summary.get("issue_count")),
            _metric("待复核抽取", summary.get("needs_review_extraction_count")),
            _metric("公式版本", audit.get("formula_version")),
            "</section>",
            '<section class="issues"><h2>问题类别</h2><ul>',
            issue_items,
            "</ul></section>",
            "<table>",
            "<thead><tr><th>叙事</th><th>证据质量</th><th>来源</th><th>抽取</th><th>陈旧/矛盾</th><th>问题</th></tr></thead>",
            f"<tbody>{rows}</tbody>",
            "</table>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _score_candidate_events(
    *,
    narrative_id: str,
    rows: list[dict[str, Any]],
    as_of: datetime,
    freshness_window_days: int,
) -> dict[str, Any]:
    issue_codes: list[str] = []
    source_types = sorted({str(row.get("source_type") or "") for row in rows})
    source_count = len({str(row.get("event_id") or "") for row in rows})
    source_diversity_score = 100.0 if source_count >= 2 and len(source_types) >= 2 else 45.0
    if source_count < 2 or len(source_types) < 2:
        issue_codes.append("LOW_SOURCE_DIVERSITY")
    extraction_items = [_extraction_item(row) for row in rows]
    extraction_scores = [float(item["extraction_confidence"]) * 100 for item in extraction_items]
    extraction_score = sum(extraction_scores) / len(extraction_scores) if extraction_scores else 0.0
    if any(item["review_status"] == "needs_review" for item in extraction_items):
        issue_codes.append("LOW_EXTRACTION_CONFIDENCE")
    reliability = _provider_reliability(rows)
    if reliability["classification"] == "blocked":
        issue_codes.append("PROVIDER_PERMISSION_BLOCKED")
    elif reliability["classification"] == "degraded":
        issue_codes.append("PROVIDER_DEGRADED")
    staleness = _staleness(rows, as_of=as_of, freshness_window_days=freshness_window_days)
    if staleness["status"] == "stale":
        issue_codes.append("STALE_EVIDENCE")
    contradiction = _contradiction(rows)
    if contradiction["status"] == "contradicted":
        issue_codes.append("CONTRADICTORY_CLAIMS")
    score = (
        source_diversity_score * 0.25
        + extraction_score * 0.25
        + float(reliability["score"]) * 0.25
        + float(staleness["score"]) * 0.15
        + float(contradiction["score"]) * 0.10
    )
    score = max(0.0, min(100.0, round(score, 1)))
    return {
        "narrative_id": narrative_id,
        "narrative_name": _narrative_name(rows, narrative_id),
        "quality_score": score,
        "quality_grade": _grade(score),
        "formula_version": QUALITY_FORMULA_VERSION,
        "issue_codes": sorted(set(issue_codes)),
        "warnings": [_warning(code) for code in sorted(set(issue_codes))],
        "components": {
            "source_diversity": {
                "score": source_diversity_score,
                "source_count": source_count,
                "source_types": source_types,
            },
            "extraction_confidence": {
                "score": round(extraction_score, 1),
                "needs_review_count": sum(
                    1 for item in extraction_items if item["review_status"] == "needs_review"
                ),
            },
            "provider_reliability": reliability,
            "recency_staleness": staleness,
            "contradiction": contradiction,
        },
        "staleness": staleness,
        "contradiction": contradiction,
        "source_lineage": [_source_lineage(row) for row in rows],
        "extraction_review": extraction_items,
        "evidence_refs": sorted(
            {
                ref
                for row in rows
                for candidate in _list(row.get("candidate_narratives"))
                if _candidate_id(candidate) == narrative_id
                for ref in _strings(candidate.get("representative_citation_ids"))
            }
        ),
        "trust_effect": "none",
        "promotion_effect": "none",
    }


def _events_by_candidate(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        for candidate in _list(event.get("candidate_narratives")):
            candidate_id = _candidate_id(candidate)
            if candidate_id:
                grouped[candidate_id].append(event)
    return dict(sorted(grouped.items()))


def _candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("candidate_narrative_id") or candidate.get("narrative_id") or "")


def _narrative_name(rows: list[dict[str, Any]], fallback: str) -> str:
    for row in rows:
        for candidate in _list(row.get("candidate_narratives")):
            name = str(candidate.get("name") or candidate.get("narrative_name") or "")
            if name:
                return name
    return fallback


def _source_lineage(event: dict[str, Any]) -> dict[str, Any]:
    metadata = _sanitize_metadata(_mapping(event.get("source_metadata")))
    return {
        "source_event_id": str(event.get("event_id") or ""),
        "source_type": str(event.get("source_type") or ""),
        "provider": str(metadata.get("provider") or "unknown_provider"),
        "provider_version": str(metadata.get("provider_version") or "unknown"),
        "permission_status": str(metadata.get("permission_status") or "not_declared"),
        "fetch_status": str(metadata.get("degradation_state") or "unknown"),
        "degradation_reason": str(metadata.get("degradation_reason") or ""),
        "source_timestamp": str(event.get("event_time") or ""),
        "ingestion_timestamp": str(event.get("ingested_at") or ""),
        "normalized_source_event_id": str(event.get("event_id") or ""),
        "reliability_classification": _lineage_reliability(metadata),
        "source_metadata": metadata,
    }


def _evidence_item_lineage(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": str(item.get("source_name") or ""),
        "source_url": str(item.get("source_url") or ""),
        "source_type": str(item.get("source_type") or ""),
        "source_timestamp": str(item.get("evidence_date") or ""),
        "supported_claim_types": _strings(item.get("supported_claim_types"))
        or _strings(item.get("supports")),
    }


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in metadata.items()
        if not any(fragment in str(key).casefold() for fragment in SECRET_KEY_FRAGMENTS)
    }


def _lineage_reliability(metadata: dict[str, Any]) -> str:
    permission = str(metadata.get("permission_status") or "").casefold()
    degradation = str(metadata.get("degradation_state") or "").casefold()
    if permission in {"provider_permission_required", "missing_permission", "blocked"}:
        return "blocked"
    if degradation in {"blocked", "contract_failed", "schema_mismatch"}:
        return "blocked"
    if degradation in {"degraded", "upstream_degraded", "request_timeout"}:
        return "degraded"
    return "reliable"


def _provider_reliability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lineages = [_source_lineage(row) for row in rows]
    classifications = {str(item["reliability_classification"]) for item in lineages}
    if "blocked" in classifications:
        classification = "blocked"
        score = 20.0
    elif "degraded" in classifications:
        classification = "degraded"
        score = 55.0
    else:
        classification = "reliable"
        score = 100.0
    return {
        "classification": classification,
        "score": score,
        "providers": sorted({str(item["provider"]) for item in lineages}),
        "permission_statuses": sorted({str(item["permission_status"]) for item in lineages}),
        "degradation_states": sorted({str(item["fetch_status"]) for item in lineages}),
    }


def _extraction_item(event: dict[str, Any]) -> dict[str, Any]:
    entities = _mapping(event.get("extracted_entities"))
    missing = [field for field in REQUIRED_ENTITY_FIELDS if not _strings(entities.get(field))]
    confidence = _event_extraction_confidence(event)
    review_status = "needs_review" if confidence < 0.6 or missing else "pass"
    return {
        "source_event_id": str(event.get("event_id") or ""),
        "source_type": str(event.get("source_type") or ""),
        "extracted_entities": {
            field: _strings(entities.get(field)) for field in REQUIRED_ENTITY_FIELDS
        },
        "extraction_confidence": round(confidence, 3),
        "missing_entity_fields": missing,
        "review_status": review_status,
        "linked_candidate_narratives": [
            _candidate_id(candidate)
            for candidate in _list(event.get("candidate_narratives"))
            if _candidate_id(candidate)
        ],
        "trust_effect": "none",
        "audit_note": "ambiguous extraction remains candidate/untrusted",
    }


def _event_extraction_confidence(event: dict[str, Any]) -> float:
    if event.get("extraction_confidence") not in (None, ""):
        return _float(event.get("extraction_confidence"))
    confidences = [
        _float(candidate.get("confidence"))
        for candidate in _list(event.get("candidate_narratives"))
        if candidate.get("confidence") not in (None, "")
    ]
    if confidences:
        return sum(confidences) / len(confidences)
    return 0.0


def _staleness(
    rows: list[dict[str, Any]],
    *,
    as_of: datetime,
    freshness_window_days: int,
) -> dict[str, Any]:
    event_times = [_parse_datetime(row.get("event_time")) for row in rows]
    event_times = [item for item in event_times if item is not None]
    if not event_times:
        return {"status": "unknown", "score": 45.0, "latest_source_timestamp": ""}
    latest = max(event_times)
    age_days = max(0, (as_of - latest).days)
    stale = age_days > freshness_window_days
    return {
        "status": "stale" if stale else "active",
        "score": 35.0 if stale else 100.0,
        "latest_source_timestamp": latest.isoformat(),
        "age_days": age_days,
        "freshness_window_days": freshness_window_days,
    }


def _contradiction(rows: list[dict[str, Any]]) -> dict[str, Any]:
    polarities_by_claim: dict[str, set[str]] = defaultdict(set)
    source_event_ids_by_claim: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        claim_type = str(row.get("claim_type") or "").strip()
        polarity = str(row.get("claim_polarity") or "").strip()
        if not claim_type or not polarity:
            continue
        polarities_by_claim[claim_type].add(polarity)
        source_event_ids_by_claim[claim_type].append(str(row.get("event_id") or ""))
    conflicts = [
        {
            "claim_type": claim_type,
            "polarities": sorted(polarities),
            "source_event_ids": sorted(source_event_ids_by_claim[claim_type]),
        }
        for claim_type, polarities in polarities_by_claim.items()
        if {"positive", "negative"}.issubset(polarities)
    ]
    return {
        "status": "contradicted" if conflicts else "clear",
        "score": 45.0 if conflicts else 100.0,
        "conflicts": conflicts,
    }


def _source_provider_summary(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for event in events:
        lineage = _source_lineage(event)
        provider = str(lineage.get("provider") or "unknown_provider")
        current = summary.setdefault(
            provider,
            {
                "event_count": 0,
                "source_types": [],
                "permission_statuses": [],
                "reliability_classifications": [],
            },
        )
        current["event_count"] += 1
        current["source_types"] = sorted(
            {*current["source_types"], str(lineage.get("source_type") or "")}
        )
        current["permission_statuses"] = sorted(
            {*current["permission_statuses"], str(lineage.get("permission_status") or "")}
        )
        current["reliability_classifications"] = sorted(
            {
                *current["reliability_classifications"],
                str(lineage.get("reliability_classification") or ""),
            }
        )
    return dict(sorted(summary.items()))


def _render_scorecard_row(item: dict[str, Any]) -> str:
    reliability = _mapping(_mapping(item.get("components")).get("provider_reliability"))
    extraction = _mapping(_mapping(item.get("components")).get("extraction_confidence"))
    return (
        "<tr>"
        f"<td><code>{_html(item.get('narrative_id'))}</code><br />{_html(item.get('narrative_name'))}</td>"
        f"<td>{_html(item.get('quality_grade'))} / {_html(item.get('quality_score'))}</td>"
        f"<td>{_html(reliability.get('classification'))}</td>"
        f"<td>{_html(extraction.get('needs_review_count'))} 待复核</td>"
        f"<td>{_html(_mapping(item.get('staleness')).get('status'))} / {_html(_mapping(item.get('contradiction')).get('status'))}</td>"
        f"<td>{_html(', '.join(_strings(item.get('issue_codes'))) or 'none')}<br />"
        f"{_html(', '.join(_source_ids(item)))}</td>"
        "</tr>"
    )


def _source_ids(item: dict[str, Any]) -> list[str]:
    return [
        str(row.get("source_event_id") or "")
        for row in _list(item.get("source_lineage"))
        if row.get("source_event_id")
    ]


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_html(label)}</span><strong>{_html(value)}</strong></div>'


def _warning(code: str) -> dict[str, str]:
    messages = {
        "LOW_SOURCE_DIVERSITY": "Evidence has insufficient source count or diversity.",
        "LOW_EXTRACTION_CONFIDENCE": "One or more source events require extraction review.",
        "PROVIDER_PERMISSION_BLOCKED": "Provider or permission state blocks full confidence.",
        "PROVIDER_DEGRADED": "Provider metadata indicates degraded source access.",
        "STALE_EVIDENCE": "Latest supporting evidence is outside the freshness window.",
        "CONTRADICTORY_CLAIMS": "Source events contain conflicting claim polarity.",
    }
    return {"code": code, "message": messages.get(code, code)}


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _latest_event_time(events: list[dict[str, Any]]) -> datetime | None:
    parsed = [_parse_datetime(event.get("event_time")) for event in events]
    parsed = [item for item in parsed if item is not None]
    return max(parsed) if parsed else None


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _html(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)
