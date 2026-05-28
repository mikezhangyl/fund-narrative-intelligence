from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.modules.narrative_intelligence.model import narrative_display_name


def aggregate_fund_narratives(
    holdings: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    holdings_by_stock = {
        holding["stock_code"]: float(holding["weight"]) for holding in holdings
    }
    exposure_by_narrative: dict[str, float] = defaultdict(float)
    confidence_numerator: dict[str, float] = defaultdict(float)

    for mapping in mappings:
        stock_code = mapping["stock_code"]
        holding_weight = holdings_by_stock.get(stock_code)
        if holding_weight is None:
            continue

        contribution = holding_weight * float(mapping["mapping_weight"])
        narrative_id = mapping["narrative_id"]
        exposure_by_narrative[narrative_id] += contribution
        confidence_numerator[narrative_id] += contribution * float(mapping["confidence"])

    total_exposure = sum(exposure_by_narrative.values())
    if total_exposure <= 0:
        return []

    exposures = []
    for narrative_id, raw_exposure in exposure_by_narrative.items():
        registry_item = registry.get(narrative_id, {})
        confidence = confidence_numerator[narrative_id] / raw_exposure
        exposures.append(
            {
                "narrative_id": narrative_id,
                "name": narrative_display_name(registry_item, narrative_id),
                "level": registry_item.get("level"),
                "raw_exposure": round(raw_exposure, 6),
                "normalized_exposure": round(raw_exposure / total_exposure, 6),
                "confidence": round(confidence, 4),
            }
        )

    return sorted(
        exposures,
        key=lambda item: (item["raw_exposure"], item["confidence"]),
        reverse=True,
    )
