from __future__ import annotations

from copy import deepcopy
from typing import Any

NARRATIVE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "N_AI": {"name_zh": "人工智能", "taxonomy_zh": "人工智能"},
    "N_AI_INFRA": {"name_zh": "人工智能基础设施", "taxonomy_zh": "人工智能"},
    "N_AI_POWER": {"name_zh": "人工智能电力需求", "taxonomy_zh": "人工智能"},
    "N_AI_APPS": {"name_zh": "人工智能应用", "taxonomy_zh": "人工智能"},
    "N_SEMI_CAPEX": {"name_zh": "半导体资本开支周期", "taxonomy_zh": "半导体"},
    "N_EV_PRICE_WAR": {"name_zh": "新能源车价格战", "taxonomy_zh": "新能源汽车"},
    "N_BAIJIU_CONSUMPTION": {"name_zh": "高端白酒消费", "taxonomy_zh": "消费"},
    "N_HEALTHCARE_INNOVATION": {"name_zh": "医疗创新", "taxonomy_zh": "医疗健康"},
    "N_NEW_ENERGY_EQUIPMENT": {"name_zh": "新能源设备", "taxonomy_zh": "新能源"},
    "N_DEFENSE_AEROSPACE": {"name_zh": "国防航天", "taxonomy_zh": "国防军工"},
    "N_REAL_ESTATE_STABILIZATION": {"name_zh": "房地产企稳", "taxonomy_zh": "房地产"},
    "N_HK_TECH_PLATFORMS": {"name_zh": "港股科技平台", "taxonomy_zh": "港股科技"},
    "C_CONSUMER_ELECTRONICS_GLOBALIZATION": {
        "name_zh": "消费电子全球化",
        "taxonomy_zh": "消费电子",
    },
    "C_DOMESTIC_DATABASE_INFRASTRUCTURE": {
        "name_zh": "国产数据库基础设施",
        "taxonomy_zh": "软件基础设施",
    },
    "C_COMMUNICATION_POWER_INFRASTRUCTURE": {
        "name_zh": "通信与电力基础设施",
        "taxonomy_zh": "基础设施设备",
    },
}


def normalize_registry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(payload)
    normalized["narratives"] = [
        normalize_narrative_entry(item) for item in normalized.get("narratives", [])
    ]
    candidate_narratives = normalized.get("candidate_narratives")
    if isinstance(candidate_narratives, list):
        normalized["candidate_narratives"] = [
            normalize_candidate_narrative(item) for item in candidate_narratives
        ]
    return normalized


def normalize_narrative_entry(narrative: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(narrative)
    translation = NARRATIVE_TRANSLATIONS.get(str(normalized.get("narrative_id") or ""), {})
    canonical_name_zh = str(
        normalized.get("canonical_name_zh")
        or translation.get("name_zh")
        or normalized.get("display_name")
        or normalized.get("name")
        or normalized.get("narrative_id")
        or ""
    )
    canonical_name_en = str(
        normalized.get("canonical_name_en")
        or normalized.get("name")
        or canonical_name_zh
    )
    canonical_taxonomy_zh = str(
        normalized.get("canonical_taxonomy_zh")
        or translation.get("taxonomy_zh")
        or normalized.get("canonical_taxonomy")
        or ""
    )
    canonical_taxonomy_en = str(
        normalized.get("canonical_taxonomy_en")
        or normalized.get("canonical_taxonomy")
        or canonical_taxonomy_zh
    )
    aliases_zh = _string_list(
        normalized.get("aliases_zh")
        or normalized.get("aliases")
        or []
    )
    aliases_en = _string_list(
        normalized.get("aliases_en")
        or normalized.get("aliases")
        or []
    )
    related_terms_zh = _string_list(
        normalized.get("related_terms_zh")
        or normalized.get("related_terms")
        or []
    )
    related_terms_en = _string_list(
        normalized.get("related_terms_en")
        or normalized.get("related_terms")
        or []
    )
    normalized.setdefault("canonical_name_zh", canonical_name_zh)
    normalized.setdefault("canonical_name_en", canonical_name_en)
    normalized.setdefault("display_name", canonical_name_zh)
    normalized.setdefault("canonical_taxonomy_zh", canonical_taxonomy_zh)
    normalized.setdefault("canonical_taxonomy_en", canonical_taxonomy_en)
    normalized.setdefault("aliases_zh", aliases_zh)
    normalized.setdefault("aliases_en", aliases_en)
    normalized.setdefault("related_terms_zh", related_terms_zh)
    normalized.setdefault("related_terms_en", related_terms_en)
    normalized.setdefault("definition_zh", canonical_name_zh)
    normalized.setdefault("definition_en", canonical_name_en)
    normalized.setdefault("inclusion_criteria_zh", [])
    normalized.setdefault("exclusion_criteria_zh", [])
    normalized.setdefault("representative_stocks", [])
    return normalized


def normalize_candidate_narrative(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(candidate)
    translation = NARRATIVE_TRANSLATIONS.get(
        str(normalized.get("candidate_narrative_id") or ""),
        {},
    )
    canonical_name_zh = str(
        normalized.get("canonical_name_zh")
        or translation.get("name_zh")
        or normalized.get("display_name")
        or normalized.get("name")
        or normalized.get("candidate_narrative_id")
        or ""
    )
    canonical_name_en = str(
        normalized.get("canonical_name_en")
        or normalized.get("name")
        or canonical_name_zh
    )
    canonical_taxonomy_zh = str(
        normalized.get("canonical_taxonomy_zh")
        or translation.get("taxonomy_zh")
        or normalized.get("canonical_taxonomy")
        or ""
    )
    canonical_taxonomy_en = str(
        normalized.get("canonical_taxonomy_en")
        or normalized.get("canonical_taxonomy")
        or canonical_taxonomy_zh
    )
    normalized.setdefault("canonical_name_zh", canonical_name_zh)
    normalized.setdefault("canonical_name_en", canonical_name_en)
    normalized.setdefault("display_name", canonical_name_zh)
    normalized.setdefault("canonical_taxonomy_zh", canonical_taxonomy_zh)
    normalized.setdefault("canonical_taxonomy_en", canonical_taxonomy_en)
    normalized.setdefault(
        "aliases_zh",
        _string_list(normalized.get("aliases_zh") or normalized.get("aliases") or []),
    )
    normalized.setdefault(
        "aliases_en",
        _string_list(normalized.get("aliases_en") or normalized.get("aliases") or []),
    )
    normalized.setdefault(
        "related_terms_zh",
        _string_list(
            normalized.get("related_terms_zh")
            or normalized.get("related_terms")
            or []
        ),
    )
    normalized.setdefault(
        "related_terms_en",
        _string_list(
            normalized.get("related_terms_en")
            or normalized.get("related_terms")
            or []
        ),
    )
    normalized.setdefault(
        "why_not_company_event_zh",
        str(normalized.get("why_not_company_event_zh") or ""),
    )
    return normalized


def narrative_display_name(narrative: dict[str, Any], fallback: str | None = None) -> str:
    return str(
        narrative.get("display_name")
        or narrative.get("canonical_name_zh")
        or narrative.get("name")
        or fallback
        or ""
    )


def narrative_taxonomy_display(
    narrative: dict[str, Any],
    fallback: str | None = None,
) -> str:
    return str(
        narrative.get("canonical_taxonomy_zh")
        or narrative.get("canonical_taxonomy")
        or fallback
        or ""
    )


def candidate_display_name(candidate: dict[str, Any], fallback: str | None = None) -> str:
    return str(
        candidate.get("display_name")
        or candidate.get("canonical_name_zh")
        or candidate.get("name")
        or fallback
        or ""
    )


def candidate_taxonomy_display(
    candidate: dict[str, Any],
    fallback: str | None = None,
) -> str:
    return str(
        candidate.get("canonical_taxonomy_zh")
        or candidate.get("canonical_taxonomy")
        or fallback
        or ""
    )


def _string_list(items: list[Any]) -> list[str]:
    return [str(item) for item in items if isinstance(item, str) and item]
