from __future__ import annotations

from collections import Counter
from typing import Any


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
            matches.append(
                {
                    "stock_code": holding["stock_code"],
                    "narrative_id": narrative_id,
                    "mapping_weight": 0.55,
                    "confidence": 0.52,
                    "method": "registry_term_rule",
                    "matched_terms": matched_terms,
                }
            )
    return matches


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
