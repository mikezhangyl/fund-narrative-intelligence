from __future__ import annotations

from collections import Counter
from typing import Any

FALLBACK_MAPPING_CONFIDENCE = 0.52
BROAD_INDUSTRY_FALLBACK_CONFIDENCE = 0.48
MULTI_MATCH_FALLBACK_CONFIDENCE = 0.42


def select_mappings_for_holdings(
    holdings: list[dict[str, Any]], mappings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    stock_codes = {holding["stock_code"] for holding in holdings}
    return [mapping for mapping in mappings if mapping["stock_code"] in stock_codes]


def build_mapping_result(
    holdings: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    exact_mappings = select_mappings_for_holdings(holdings, mappings)
    mapped_stock_codes = {mapping["stock_code"] for mapping in exact_mappings}
    fallback_mappings = [
        fallback
        for holding in holdings
        if holding["stock_code"] not in mapped_stock_codes
        for fallback in _fallback_mappings_for_holding(holding, registry)
    ]
    all_mappings = [*exact_mappings, *fallback_mappings]
    covered_stock_codes = {mapping["stock_code"] for mapping in all_mappings}
    unmapped_holdings = [
        holding for holding in holdings if holding["stock_code"] not in covered_stock_codes
    ]

    return {
        "mappings": all_mappings,
        "coverage": _coverage(holdings, all_mappings, unmapped_holdings),
        "unmapped_holdings": unmapped_holdings,
        "mapping_rationales": _mapping_rationales(
            holdings=holdings,
            mappings=all_mappings,
            registry=registry,
        ),
        "mapping_precision_flags": _mapping_precision_flags(
            holdings=holdings,
            mappings=fallback_mappings,
            registry=registry,
        ),
    }


def _fallback_mappings_for_holding(
    holding: dict[str, Any], registry: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    haystack = " ".join(
        str(value)
        for value in [
            holding.get("stock_code", ""),
            holding.get("stock_name", ""),
            holding.get("industry", ""),
        ]
    ).lower()
    matches = []
    for narrative_id, narrative in registry.items():
        terms = _registry_terms(narrative)
        matched_terms = [
            term for term in terms if term.lower() and term.lower() in haystack
        ]
        if matched_terms:
            precision_fields = {}
            if _is_broad_industry_only_fallback(holding, matched_terms):
                precision_fields = {
                    "confidence": BROAD_INDUSTRY_FALLBACK_CONFIDENCE,
                    "needs_review": True,
                    "precision_flag": "broad_industry_fallback",
                }
            matches.append(
                {
                    "stock_code": holding["stock_code"],
                    "narrative_id": narrative_id,
                    "mapping_weight": 0.55,
                    "confidence": FALLBACK_MAPPING_CONFIDENCE,
                    "method": "registry_term_rule",
                    "matched_terms": matched_terms,
                    **precision_fields,
                }
            )
    if len(matches) <= 1:
        return matches
    return [
        {
            **match,
            "confidence": MULTI_MATCH_FALLBACK_CONFIDENCE,
            "needs_review": True,
            "precision_flag": "multi_match_fallback",
        }
        for match in matches
    ]


def _mapping_precision_flags(
    holdings: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    holdings_by_code = {holding["stock_code"]: holding for holding in holdings}
    mappings_by_stock: dict[str, list[dict[str, Any]]] = {}
    flags = []
    for mapping in mappings:
        if mapping.get("precision_flag") == "broad_industry_fallback":
            holding = holdings_by_code.get(mapping["stock_code"], {})
            narrative_id = mapping["narrative_id"]
            flags.append(
                {
                    "type": "broad_industry_fallback",
                    "severity": "watch",
                    "stock_code": mapping["stock_code"],
                    "stock_name": holding.get("stock_name"),
                    "industry": holding.get("industry"),
                    "weight": holding.get("weight"),
                    "mapping_method": "registry_term_rule",
                    "narrative_ids": [narrative_id],
                    "narratives": [
                        registry.get(narrative_id, {}).get("name", narrative_id)
                    ],
                    "confidence_before": FALLBACK_MAPPING_CONFIDENCE,
                    "confidence_after": BROAD_INDUSTRY_FALLBACK_CONFIDENCE,
                    "recommended_action": "curation_review",
                }
            )
            continue
        if mapping.get("precision_flag") != "multi_match_fallback":
            continue
        mappings_by_stock.setdefault(mapping["stock_code"], []).append(mapping)

    for stock_code, stock_mappings in sorted(mappings_by_stock.items()):
        holding = holdings_by_code.get(stock_code, {})
        narrative_ids = [mapping["narrative_id"] for mapping in stock_mappings]
        flags.append(
            {
                "type": "multi_match_fallback",
                "severity": "review",
                "stock_code": stock_code,
                "stock_name": holding.get("stock_name"),
                "industry": holding.get("industry"),
                "weight": holding.get("weight"),
                "mapping_method": "registry_term_rule",
                "narrative_ids": narrative_ids,
                "narratives": [
                    registry.get(narrative_id, {}).get("name", narrative_id)
                    for narrative_id in narrative_ids
                ],
                "confidence_before": FALLBACK_MAPPING_CONFIDENCE,
                "confidence_after": MULTI_MATCH_FALLBACK_CONFIDENCE,
                "recommended_action": "manual_review",
            }
        )
    return flags


def _mapping_rationales(
    holdings: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    holdings_by_code = {holding["stock_code"]: holding for holding in holdings}
    rationales = []
    for mapping in mappings:
        holding = holdings_by_code.get(mapping["stock_code"], {})
        narrative_id = mapping["narrative_id"]
        matched_terms = [str(term) for term in mapping.get("matched_terms", [])]
        method = str(mapping.get("method", "unknown"))
        rationales.append(
            {
                "stock_code": mapping["stock_code"],
                "stock_name": holding.get("stock_name"),
                "industry": holding.get("industry"),
                "narrative_id": narrative_id,
                "narrative_name": registry.get(narrative_id, {}).get(
                    "name", narrative_id
                ),
                "method": method,
                "confidence": mapping["confidence"],
                "mapping_weight": mapping["mapping_weight"],
                "matched_terms": matched_terms,
                "needs_review": bool(mapping.get("needs_review", False)),
                "precision_flag": mapping.get("precision_flag"),
                "reason": _mapping_reason(
                    method=method,
                    matched_terms=matched_terms,
                    precision_flag=mapping.get("precision_flag"),
                ),
            }
        )
    return rationales


def _mapping_reason(
    method: str,
    matched_terms: list[str],
    precision_flag: Any,
) -> str:
    if precision_flag == "broad_industry_fallback" and matched_terms:
        return (
            "Matched broad industry-only registry terms against holding industry: "
            f"{', '.join(matched_terms)}."
        )
    if matched_terms:
        return (
            "Matched registry terms against stock code/name/industry: "
            f"{', '.join(matched_terms)}."
        )
    if method == "fixture_rule":
        return "Explicit fixture_rule mapping from the stock-narrative mapping fixture."
    return f"{method} mapping without term-level rationale."


def _is_broad_industry_only_fallback(
    holding: dict[str, Any], matched_terms: list[str]
) -> bool:
    stock_text = " ".join(
        str(value)
        for value in [
            holding.get("stock_code", ""),
            holding.get("stock_name", ""),
        ]
    ).lower()
    industry_text = str(holding.get("industry", "")).lower()
    return bool(matched_terms) and all(
        term.lower() in industry_text and term.lower() not in stock_text
        for term in matched_terms
    )


def _registry_terms(narrative: dict[str, Any]) -> list[str]:
    raw_terms = [
        narrative.get("name", ""),
        *narrative.get("aliases", []),
        *narrative.get("related_terms", []),
    ]
    return [str(term).strip() for term in raw_terms if str(term).strip()]


def _coverage(
    holdings: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    unmapped_holdings: list[dict[str, Any]],
) -> dict[str, Any]:
    total_weight = sum(float(holding["weight"]) for holding in holdings)
    unmapped_weight = sum(float(holding["weight"]) for holding in unmapped_holdings)
    covered_weight = total_weight - unmapped_weight
    method_counts = Counter(mapping.get("method", "unknown") for mapping in mappings)
    return {
        "total_holding_count": len(holdings),
        "covered_holding_count": len(holdings) - len(unmapped_holdings),
        "unmapped_holding_count": len(unmapped_holdings),
        "total_weight": round(total_weight, 6),
        "covered_weight": round(covered_weight, 6),
        "unmapped_weight": round(unmapped_weight, 6),
        "coverage_ratio": round(covered_weight / total_weight, 6)
        if total_weight
        else 0,
        "mapping_methods": dict(sorted(method_counts.items())),
    }
