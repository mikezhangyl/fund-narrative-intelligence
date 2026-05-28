from __future__ import annotations

from collections import Counter
from typing import Any

from src.modules.narrative_intelligence.model import narrative_display_name

_INDUSTRY_TRANSLATIONS = {
    "communications infrastructure": ("通信基础设施", "Communications Infrastructure"),
    "communication equipment": ("通信设备", "Communication Equipment"),
    "communications equipment": ("通信设备", "Communication Equipment"),
    "cloud infrastructure": ("云基础设施", "Cloud Infrastructure"),
    "software": ("软件", "Software"),
    "electronics": ("电子", "Electronics"),
}

_FACT_TAG_RULES = [
    {
        "tag_name_zh": "光模块",
        "tag_name_en": "Optical Module",
        "patterns": [
            "光模块",
            "800g光模块",
            "400g光模块",
            "光器件",
            "eoptolink",
            "innolight",
            "accelink",
        ],
    },
    {
        "tag_name_zh": "光通信",
        "tag_name_en": "Optical Communication",
        "patterns": [
            "光通信",
            "光电",
            "光纤",
            "光缆",
            "光迅",
            "optic-electric",
            "optical commun",
            "fiberhome telecommunications",
            "telecommunications",
        ],
    },
    {
        "tag_name_zh": "光互联",
        "tag_name_en": "Optical Interconnect",
        "patterns": ["光互联", "optical interconnect", "interconnect"],
    },
    {
        "tag_name_zh": "海缆",
        "tag_name_en": "Submarine Cable",
        "patterns": ["海缆", "submarine cable"],
    },
    {
        "tag_name_zh": "白酒",
        "tag_name_en": "Baijiu",
        "patterns": ["白酒", "baijiu"],
    },
]

_COMPANY_IDENTITY_RULES = [
    {
        "tag_name_zh": "光模块",
        "tag_name_en": "Optical Module",
        "company_patterns_zh": [
            "新易盛",
            "中际旭创",
            "天孚通信",
        ],
        "company_patterns_en": [
            "eoptolink",
            "innolight",
            "accelink",
        ],
    },
    {
        "tag_name_zh": "光通信",
        "tag_name_en": "Optical Communication",
        "company_patterns_zh": [
            "光迅科技",
            "亨通光电",
            "烽火通信",
            "中天科技",
        ],
        "company_patterns_en": [
            "optic-electric",
            "optical commun",
            "fiberhome telecommunications",
            "telecommunications",
        ],
    },
    {
        "tag_name_zh": "光互联",
        "tag_name_en": "Optical Interconnect",
        "company_patterns_zh": [],
        "company_patterns_en": ["optical interconnect", "interconnect"],
    },
    {
        "tag_name_zh": "海缆",
        "tag_name_en": "Submarine Cable",
        "company_patterns_zh": ["海缆"],
        "company_patterns_en": ["submarine cable"],
    },
    {
        "tag_name_zh": "白酒",
        "tag_name_en": "Baijiu",
        "company_patterns_zh": ["舍得酒业", "迎驾贡酒", "贵州茅台", "五粮液", "泸州老窖"],
        "company_patterns_en": ["baijiu"],
    },
]


def build_company_exposure_tags(
    *,
    holdings: list[dict[str, Any]],
    company_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    facts_by_stock: dict[str, list[dict[str, Any]]] = {}
    for fact in company_facts:
        stock_code = str(fact.get("stock_code") or "")
        if stock_code:
            facts_by_stock.setdefault(stock_code, []).append(fact)

    tags: list[dict[str, Any]] = []
    for holding in holdings:
        stock_code = str(holding.get("stock_code") or "")
        stock_name = str(holding.get("stock_name") or "")
        industry_tag = _industry_tag(holding)
        if industry_tag is not None:
            tags.append(
                {
                    "company_exposure_tag_id": f"TAG_{stock_code}_{industry_tag['tag_name_zh']}",
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "tag_name_zh": industry_tag["tag_name_zh"],
                    "tag_name_en": industry_tag["tag_name_en"],
                    "tag_source": "holding_industry",
                    "tag_confidence": 0.72,
                    "supporting_company_fact_ids": [],
                }
            )

        fact_tag = _fact_driven_tag(
            stock_code=stock_code,
            stock_name=stock_name,
            company_facts=facts_by_stock.get(stock_code, []),
        )
        if fact_tag is not None:
            tags.append(fact_tag)
        name_tag = _company_name_tag(
            stock_code=stock_code,
            stock_name=stock_name,
            company_facts=facts_by_stock.get(stock_code, []),
        )
        if (
            name_tag is not None
            and not (
                fact_tag is not None
                and fact_tag.get("tag_name_zh") == name_tag.get("tag_name_zh")
            )
        ):
            tags.append(name_tag)

    tags = sorted(
        _dedupe_tags(tags),
        key=lambda item: (
            str(item.get("stock_code") or ""),
            str(item.get("tag_source") or ""),
            str(item.get("tag_name_zh") or ""),
        ),
    )
    return {
        "items": tags,
        "stats": {
            "tag_count": len(tags),
            "stock_coverage_count": len(
                {
                    str(item.get("stock_code") or "")
                    for item in tags
                    if item.get("stock_code")
                }
            ),
            "source_counts": dict(
                sorted(Counter(str(item.get("tag_source") or "") for item in tags).items())
            ),
        },
    }


def aggregate_fund_exposure_tags(
    *,
    holdings: list[dict[str, Any]],
    company_exposure_tags: list[dict[str, Any]],
    registry_items: list[dict[str, Any]],
) -> dict[str, Any]:
    weights_by_stock = {
        str(holding.get("stock_code") or ""): float(holding.get("weight") or 0)
        for holding in holdings
        if holding.get("stock_code")
    }
    names_by_stock = {
        str(holding.get("stock_code") or ""): str(holding.get("stock_name") or "")
        for holding in holdings
        if holding.get("stock_code")
    }
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for tag in company_exposure_tags:
        stock_code = str(tag.get("stock_code") or "")
        key = (
            str(tag.get("tag_name_zh") or ""),
            str(tag.get("tag_name_en") or ""),
        )
        if not stock_code or not key[0]:
            continue
        current = grouped.setdefault(
            key,
            {
                "tag_name_zh": key[0],
                "tag_name_en": key[1],
                "raw_exposure": 0.0,
                "confidence_numerator": 0.0,
                "stock_codes": set(),
                "stock_names": set(),
                "supporting_company_fact_ids": set(),
            },
        )
        stock_weight = weights_by_stock.get(stock_code, 0.0)
        confidence = float(tag.get("tag_confidence") or 0)
        current["raw_exposure"] += stock_weight
        current["confidence_numerator"] += stock_weight * confidence
        current["stock_codes"].add(stock_code)
        if names_by_stock.get(stock_code):
            current["stock_names"].add(names_by_stock[stock_code])
        current["supporting_company_fact_ids"].update(
            str(item) for item in tag.get("supporting_company_fact_ids") or []
        )

    total_exposure = sum(item["raw_exposure"] for item in grouped.values())
    aggregated_items = []
    linked_count = 0
    for group in grouped.values():
        raw_exposure = round(group["raw_exposure"], 6)
        confidence = (
            round(group["confidence_numerator"] / group["raw_exposure"], 2)
            if group["raw_exposure"] > 0
            else 0.0
        )
        links = _link_tag_to_narratives(
            tag_name_zh=group["tag_name_zh"],
            tag_name_en=group["tag_name_en"],
            registry_items=registry_items,
        )
        if links["linked_narrative_ids"]:
            linked_count += 1
        aggregated_items.append(
            {
                "tag_name_zh": group["tag_name_zh"],
                "tag_name_en": group["tag_name_en"],
                "raw_exposure": raw_exposure,
                "normalized_exposure": round(raw_exposure / total_exposure, 6)
                if total_exposure > 0
                else 0.0,
                "confidence": confidence,
                "stock_codes": sorted(group["stock_codes"]),
                "stock_names": sorted(group["stock_names"]),
                "supporting_company_fact_ids": sorted(
                    group["supporting_company_fact_ids"]
                ),
                **links,
            }
        )
    aggregated_items.sort(
        key=lambda item: (item["raw_exposure"], item["confidence"], item["tag_name_zh"]),
        reverse=True,
    )
    return {
        "items": aggregated_items,
        "stats": {
            "tag_count": len(aggregated_items),
            "linked_tag_count": linked_count,
            "stock_coverage_count": len(
                {
                    stock_code
                    for item in aggregated_items
                    for stock_code in item["stock_codes"]
                }
            ),
        },
    }


def _industry_tag(holding: dict[str, Any]) -> dict[str, str] | None:
    industry = str(holding.get("industry") or "").strip()
    if not industry:
        return None
    translated = _INDUSTRY_TRANSLATIONS.get(industry.lower())
    if translated is not None:
        return {"tag_name_zh": translated[0], "tag_name_en": translated[1]}
    if _contains_cjk(industry):
        return {"tag_name_zh": industry, "tag_name_en": _industry_en_guess(industry)}
    return None


def _fact_driven_tag(
    *,
    stock_code: str,
    stock_name: str,
    company_facts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    ready_facts = [fact for fact in company_facts if fact.get("narrative_ready")]
    if not ready_facts:
        return None
    for rule in _FACT_TAG_RULES:
        supporting_ids = [
            str(fact.get("company_fact_id"))
            for fact in ready_facts
            if _fact_matches_rule(fact, rule["patterns"])
        ]
        if not supporting_ids:
            continue
        confidence = 0.74 if len(supporting_ids) >= 2 else 0.68
        return {
            "company_exposure_tag_id": f"TAG_{stock_code}_{rule['tag_name_zh']}",
            "stock_code": stock_code,
            "stock_name": stock_name,
            "tag_name_zh": rule["tag_name_zh"],
            "tag_name_en": rule["tag_name_en"],
            "tag_source": "company_fact_keyword",
            "tag_confidence": confidence,
            "supporting_company_fact_ids": supporting_ids,
        }
    return None


def _company_name_tag(
    *,
    stock_code: str,
    stock_name: str,
    company_facts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    zh_match: dict[str, Any] | None = None
    en_match: dict[str, Any] | None = None
    for rule in _COMPANY_IDENTITY_RULES:
        zh_supporting_ids = [
            str(fact.get("company_fact_id"))
            for fact in company_facts
            if _fact_matches_company_identity_zh(
                fact,
                company_patterns_zh=rule["company_patterns_zh"],
            )
        ]
        if zh_supporting_ids and zh_match is None:
            confidence = 0.76 if len(zh_supporting_ids) >= 2 else 0.7
            zh_match = {
                "company_exposure_tag_id": f"TAG_{stock_code}_{rule['tag_name_zh']}",
                "stock_code": stock_code,
                "stock_name": stock_name,
                "tag_name_zh": rule["tag_name_zh"],
                "tag_name_en": rule["tag_name_en"],
                "tag_source": "company_name_keyword",
                "tag_confidence": confidence,
                "supporting_company_fact_ids": sorted(set(zh_supporting_ids)),
            }
            continue
        en_supporting_ids = [
            str(fact.get("company_fact_id"))
            for fact in company_facts
            if _fact_matches_company_identity_en(
                fact,
                company_patterns_en=rule["company_patterns_en"],
            )
        ]
        if not en_supporting_ids or en_match is not None:
            continue
        confidence = 0.76 if len(en_supporting_ids) >= 2 else 0.7
        en_match = {
            "company_exposure_tag_id": f"TAG_{stock_code}_{rule['tag_name_zh']}",
            "stock_code": stock_code,
            "stock_name": stock_name,
            "tag_name_zh": rule["tag_name_zh"],
            "tag_name_en": rule["tag_name_en"],
            "tag_source": "company_name_keyword",
            "tag_confidence": confidence,
            "supporting_company_fact_ids": sorted(set(en_supporting_ids)),
        }
    return zh_match or en_match


def _fact_matches_rule(fact: dict[str, Any], patterns: list[str]) -> bool:
    company_identity_terms = {
        str(item).lower()
        for item in [
            *(fact.get("company_keywords_zh") or []),
            *(fact.get("company_keywords_en") or []),
        ]
        if str(item).strip()
    }
    texts = [
        *[
            str(item)
            for item in fact.get("event_keywords_zh") or []
            if str(item).lower() not in company_identity_terms
        ],
        *[
            str(item)
            for item in fact.get("event_keywords_en") or []
            if str(item).lower() not in company_identity_terms
        ],
    ]
    haystack = " ".join(texts).lower()
    return any(pattern.lower() in haystack for pattern in patterns)


def _fact_matches_company_identity_zh(
    fact: dict[str, Any],
    *,
    company_patterns_zh: list[str],
) -> bool:
    zh_terms = " ".join(
        str(item) for item in fact.get("company_keywords_zh") or [] if str(item).strip()
    )
    return any(pattern in zh_terms for pattern in company_patterns_zh)


def _fact_matches_company_identity_en(
    fact: dict[str, Any],
    *,
    company_patterns_en: list[str],
) -> bool:
    en_terms = " ".join(
        str(item).lower()
        for item in fact.get("company_keywords_en") or []
        if str(item).strip()
    )
    return any(pattern.lower() in en_terms for pattern in company_patterns_en)


def _industry_en_guess(industry: str) -> str:
    guesses = {
        "通信设备": "Communication Equipment",
        "通信基础设施": "Communications Infrastructure",
        "云基础设施": "Cloud Infrastructure",
        "电子": "Electronics",
        "软件": "Software",
        "食品饮料": "Food and Beverage",
    }
    return guesses.get(industry, industry)


def _dedupe_tags(tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for tag in tags:
        key = (
            str(tag.get("stock_code") or ""),
            str(tag.get("tag_name_zh") or ""),
            str(tag.get("tag_source") or ""),
        )
        if key not in deduped:
            deduped[key] = tag
            continue
        current = deduped[key]
        current["supporting_company_fact_ids"] = sorted(
            {
                *current.get("supporting_company_fact_ids", []),
                *tag.get("supporting_company_fact_ids", []),
            }
        )
        current["tag_confidence"] = max(
            float(current.get("tag_confidence") or 0),
            float(tag.get("tag_confidence") or 0),
        )
    return list(deduped.values())


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _link_tag_to_narratives(
    *,
    tag_name_zh: str,
    tag_name_en: str,
    registry_items: list[dict[str, Any]],
) -> dict[str, Any]:
    linked_ids = []
    linked_names = []
    best_confidence = None
    for narrative in registry_items:
        terms = _narrative_terms(narrative)
        if tag_name_zh in terms or tag_name_en.lower() in terms:
            linked_ids.append(str(narrative.get("narrative_id") or ""))
            linked_names.append(
                narrative_display_name(
                    narrative,
                    str(narrative.get("narrative_id") or ""),
                )
            )
            best_confidence = max(best_confidence or 0, 0.78)
    return {
        "linked_narrative_ids": linked_ids,
        "linked_narrative_names": linked_names,
        "link_method": "registry_tag_term_match" if linked_ids else None,
        "link_confidence": best_confidence,
    }


def _narrative_terms(narrative: dict[str, Any]) -> set[str]:
    terms = {
        str(narrative.get("canonical_name_zh") or ""),
        str(narrative.get("canonical_name_en") or "").lower(),
        str(narrative.get("display_name") or ""),
        str(narrative.get("name") or ""),
        str(narrative.get("canonical_taxonomy_zh") or ""),
        str(narrative.get("canonical_taxonomy_en") or "").lower(),
        str(narrative.get("canonical_taxonomy") or "").lower(),
    }
    terms.update(str(item) for item in narrative.get("aliases_zh") or [])
    terms.update(str(item).lower() for item in narrative.get("aliases_en") or [])
    terms.update(str(item) for item in narrative.get("related_terms_zh") or [])
    terms.update(str(item).lower() for item in narrative.get("related_terms_en") or [])
    terms.update(str(item) for item in narrative.get("aliases") or [])
    terms.update(str(item).lower() for item in narrative.get("related_terms") or [])
    return {term for term in terms if term}
