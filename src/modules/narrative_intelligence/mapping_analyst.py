from __future__ import annotations

from typing import Any

MAPPING_PROPOSAL_VERSION = "narrative-mapping-proposals-v1"


def build_mapping_proposals(
    *,
    generated_candidates: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    source_catalog: dict[str, Any],
) -> dict[str, Any]:
    holdings_by_stock = {
        str(holding.get("stock_code") or ""): holding for holding in holdings
    }
    source_items_by_stock: dict[str, list[dict[str, Any]]] = {}
    for item in source_catalog.get("items") or []:
        stock_code = str(item.get("stock_code") or "")
        if stock_code:
            source_items_by_stock.setdefault(stock_code, []).append(item)
    proposals = []
    for candidate in generated_candidates:
        candidate_id = str(candidate.get("candidate_narrative_id") or "")
        if not candidate_id:
            continue
        for stock_code in candidate.get("triggering_stock_codes") or []:
            holding = holdings_by_stock.get(stock_code, {})
            source_items = source_items_by_stock.get(stock_code, [])
            proposals.append(
                {
                    "proposal_id": f"MAP_{candidate_id}_{stock_code}",
                    "proposal_type": "candidate_mapping",
                    "stock_code": stock_code,
                    "stock_name": holding.get("stock_name"),
                    "industry": holding.get("industry"),
                    "holding_weight": holding.get("weight"),
                    "candidate_narrative_id": candidate_id,
                    "candidate_name": candidate.get("name"),
                    "proposed_mapping_weight": 0.55,
                    "confidence": round(
                        min(
                            float(candidate.get("confidence") or 0.5)
                            * (1 + 0.04 * min(len(source_items), 4)),
                            0.9,
                        ),
                        3,
                    ),
                    "rationale": (
                        f"Proposed from {len(source_items)} supporting source items and "
                        f"candidate terms {', '.join(candidate.get('related_terms', [])[:3])}."
                    ),
                    "supporting_source_item_ids": [
                        str(item.get("source_item_id"))
                        for item in source_items[:5]
                    ],
                    "status": "proposed",
                }
            )
    return {
        "version": MAPPING_PROPOSAL_VERSION,
        "items": proposals,
        "summary": {"proposal_count": len(proposals)},
    }
