from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
from time import sleep
from typing import Any, Protocol
from urllib import error, request

from src.local_env import get_config_value
from src.modules.narrative_intelligence.model import normalize_candidate_narrative
from src.modules.narrative_intelligence.source_scout import normalized_terms

CANDIDATE_SEED_VERSION = "narrative-candidate-seeds-v1"
GENERATED_CANDIDATE_VERSION = "generated-candidate-narratives-v1"

_MIN_SUPPORTING_ITEMS = 2
_MIN_DISTINCT_TERMS = 1


class NarrativeCurator(Protocol):
    def curate_candidate(
        self,
        *,
        seed: dict[str, Any],
        source_items: list[dict[str, Any]],
        holdings: list[dict[str, Any]],
        ) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class NarrativeCurationError(Exception):
    provider_name: str
    provider_version: str
    model: str
    reason: str
    attempt_count: int

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True)
class DeterministicNarrativeCurator:
    provider_name: str = "deterministic-narrative-curator"
    provider_version: str = "deterministic-narrative-curator-v1"

    def curate_candidate(
        self,
        *,
        seed: dict[str, Any],
        source_items: list[dict[str, Any]],
        holdings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        holding_names_zh = _holding_names_zh(holdings)
        holding_names = sorted(
            {
                str(item.get("stock_name") or "")
                for item in holdings
                if item.get("stock_name")
            }
        )
        industries = sorted(
            {
                str(item.get("industry") or "")
                for item in holdings
                if item.get("industry")
            }
        )
        key_terms = list(seed.get("key_terms") or [])
        primary_phrase = " ".join(key_terms[:2]).strip() or "Emerging Narrative"
        if _contains_cjk(primary_phrase):
            candidate_name = primary_phrase
        else:
            candidate_name = primary_phrase.title()
        canonical_taxonomy = industries[0] if industries else "Emerging Theme"
        first_seen_at = seed.get("first_seen_at") or _today_date()
        support_item_ids = list(seed.get("supporting_source_item_ids") or [])
        representative_citations = [
            _citation_from_source_item(item)
            for item in source_items
            if item.get("source_item_id") in support_item_ids
        ][:3]
        confidence = round(
            min(
                0.55
                + 0.08 * max(len(key_terms) - 1, 0)
                + 0.05 * max(len(holdings) - 1, 0)
                + 0.04 * max(len(representative_citations) - 1, 0),
                0.88,
            ),
            3,
        )
        canonical_name_zh = _candidate_name_zh(
            key_terms=key_terms,
            holdings=holdings,
            fallback_name=candidate_name,
        )
        canonical_taxonomy_zh = _taxonomy_zh(
            industries=industries,
            fallback=canonical_taxonomy,
        )
        return {
            "candidate_narrative_id": _candidate_narrative_id(seed),
            "name": candidate_name,
            "canonical_name_zh": canonical_name_zh,
            "canonical_name_en": candidate_name,
            "display_name": canonical_name_zh,
            "canonical_taxonomy": canonical_taxonomy,
            "canonical_taxonomy_zh": canonical_taxonomy_zh,
            "canonical_taxonomy_en": canonical_taxonomy,
            "status": "candidate",
            "source": "narrative_intelligence_generation",
            "triggering_stock_codes": list(seed.get("triggering_stock_codes") or []),
            "related_exclusion_ids": list(seed.get("related_exclusion_ids") or []),
            "aliases": _aliases(candidate_name, key_terms),
            "aliases_zh": _aliases_zh(canonical_name_zh, key_terms, holding_names_zh),
            "aliases_en": _aliases(candidate_name, key_terms),
            "related_terms": key_terms,
            "related_terms_zh": _related_terms_zh(key_terms, holdings),
            "related_terms_en": key_terms,
            "rationale": (
                f"Generated from {len(representative_citations)} cited source items across "
                f"{len(holdings)} holding(s): {', '.join(holding_names[:3]) or 'unknown holdings'}."
            ),
            "human_review_status": "candidate",
            "reviewed_by": None,
            "reviewed_at": None,
            "first_seen_at": first_seen_at,
            "last_updated_at": first_seen_at,
            "definition": _definition(candidate_name, key_terms, industries, holdings),
            "definition_zh": _definition_zh(
                candidate_name=canonical_name_zh,
                key_terms=key_terms,
                industries=industries,
                holdings=holdings,
            ),
            "definition_en": _definition(candidate_name, key_terms, industries, holdings),
            "inclusion_criteria": _inclusion_criteria(key_terms, holdings),
            "inclusion_criteria_zh": _inclusion_criteria_zh(key_terms, holdings),
            "exclusion_criteria": _exclusion_criteria(industries),
            "exclusion_criteria_zh": _exclusion_criteria_zh(industries),
            "why_not_company_event_zh": _why_not_company_event_zh(seed, holdings),
            "representative_citations": representative_citations,
            "confidence": confidence,
            "derivation": {
                "seed_id": seed.get("seed_id"),
                "curation_provider": self.provider_name,
                "curation_provider_version": self.provider_version,
                "supporting_source_item_ids": support_item_ids,
                "source_item_count": len(source_items),
                "holding_count": len(holdings),
            },
        }


@dataclass(frozen=True)
class OpenAINarrativeCurator:
    api_key: str
    model: str = "MiniMax-M2.7"
    api_url: str = "https://api.openai.com/v1/responses"
    timeout_seconds: int = 30
    max_attempts: int = 3
    retry_delay_seconds: float = 1.0

    provider_name: str = "openai-narrative-curator"
    provider_version: str = "openai-responses-v1"

    def curate_candidate(
        self,
        *,
        seed: dict[str, Any],
        source_items: list[dict[str, Any]],
        holdings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fallback = DeterministicNarrativeCurator().curate_candidate(
            seed=seed,
            source_items=source_items,
            holdings=holdings,
        )
        request_body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You curate candidate market narratives for an investment research system. "
                                "Only use provided facts. Do not invent URLs, dates, or cited items. "
                                "Return JSON matching the schema."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                {
                                    "seed": seed,
                                    "holdings": holdings,
                                    "source_items": source_items,
                                    "fallback_candidate": fallback,
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "candidate_narrative",
                    "strict": True,
                    "schema": _candidate_schema(),
                }
            },
        }
        last_reason = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                payload = _post_json(
                    url=self.api_url,
                    **{"api_key": self.api_key},
                    body=request_body,
                    timeout_seconds=self.timeout_seconds,
                )
                candidate = _parse_json_text(_response_output_text(payload))
                break
            except Exception as exc:
                last_reason = str(exc)
                if attempt >= self.max_attempts:
                    raise NarrativeCurationError(
                        provider_name=self.provider_name,
                        provider_version=self.provider_version,
                        model=self.model,
                        reason=last_reason,
                        attempt_count=attempt,
                    ) from exc
                sleep(self.retry_delay_seconds * attempt)
        curated = {
            **fallback,
            **candidate,
            "status": "candidate",
            "source": "narrative_intelligence_generation",
            "human_review_status": "candidate",
            "reviewed_by": None,
            "reviewed_at": None,
            "first_seen_at": fallback["first_seen_at"],
            "last_updated_at": fallback["last_updated_at"],
        }
        curated["representative_citations"] = _curation_citations(
            requested_ids=curated.get("representative_citation_ids") or [],
            fallback_citations=fallback["representative_citations"],
        )
        curated["derivation"] = {
            **deepcopy(fallback["derivation"]),
            "curation_provider": self.provider_name,
            "curation_provider_version": self.provider_version,
            "model": self.model,
        }
        return curated


@dataclass(frozen=True)
class MiniMaxNarrativeCurator:
    api_key: str
    model: str = "MiniMax-M2.7"
    base_url: str = "https://api.minimaxi.com/anthropic"
    max_tokens: int = 1600
    max_attempts: int = 3
    retry_delay_seconds: float = 1.0

    provider_name: str = "minimax-narrative-curator"
    provider_version: str = "anthropic-compatible-v1"

    def curate_candidate(
        self,
        *,
        seed: dict[str, Any],
        source_items: list[dict[str, Any]],
        holdings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fallback = DeterministicNarrativeCurator().curate_candidate(
            seed=seed,
            source_items=source_items,
            holdings=holdings,
        )
        anthropic_module = import_module("anthropic")
        client = anthropic_module.Anthropic(
            base_url=self.base_url,
            **{"api_key": self.api_key},
        )
        request_payload = _curation_request_payload(
            seed=seed,
            holdings=holdings,
            source_items=source_items,
            fallback=fallback,
        )
        last_reason = ""
        candidate: dict[str, Any] | None = None
        for attempt in range(1, self.max_attempts + 1):
            message = None
            try:
                message = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=_minimax_system_prompt(),
                    messages=[
                        {
                            "role": "user",
                            "content": request_payload,
                        }
                    ],
                )
                response_text = _anthropic_message_text(message)
                candidate = _parse_json_text(response_text)
                break
            except Exception as exc:
                last_reason = _minimax_failure_reason(exc=exc, message=message)
                if attempt >= self.max_attempts:
                    raise NarrativeCurationError(
                        provider_name=self.provider_name,
                        provider_version=self.provider_version,
                        model=self.model,
                        reason=last_reason,
                        attempt_count=attempt,
                    ) from exc
                sleep(self.retry_delay_seconds * attempt)
        if candidate is None:
            raise NarrativeCurationError(
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                model=self.model,
                reason=last_reason or "MiniMax narrative curation did not return a candidate",
                attempt_count=self.max_attempts,
            )
        curated = {
            **fallback,
            **candidate,
            "status": "candidate",
            "source": "narrative_intelligence_generation",
            "human_review_status": "candidate",
            "reviewed_by": None,
            "reviewed_at": None,
            "first_seen_at": fallback["first_seen_at"],
            "last_updated_at": fallback["last_updated_at"],
        }
        curated["representative_citations"] = _curation_citations(
            requested_ids=curated.get("representative_citation_ids") or [],
            fallback_citations=fallback["representative_citations"],
        )
        curated["derivation"] = {
            **deepcopy(fallback["derivation"]),
            "curation_provider": self.provider_name,
            "curation_provider_version": self.provider_version,
            "model": self.model,
        }
        return curated


def select_narrative_curator(
    mode: str,
    *,
    model: str,
) -> NarrativeCurator:
    if mode == "deterministic":
        return DeterministicNarrativeCurator()
    if mode == "minimax":
        api_key = get_config_value("MINIMAX_API_KEY")
        if not api_key:
            raise ValueError(
                "MINIMAX_API_KEY is required for narrative_curator_mode=minimax"
            )
        return MiniMaxNarrativeCurator(
            **{"api_key": api_key},
            model=model,
            base_url=(
                get_config_value("MINIMAX_ANTHROPIC_BASE_URL")
                or "https://api.minimaxi.com/anthropic"
            ),
        )
    if mode == "openai":
        api_key = get_config_value("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for narrative_curator_mode=openai")
        return OpenAINarrativeCurator(**{"api_key": api_key}, model=model)
    if mode == "auto":
        minimax_api_key = get_config_value("MINIMAX_API_KEY")
        if minimax_api_key:
            return MiniMaxNarrativeCurator(
                **{"api_key": minimax_api_key},
                model=model,
                base_url=(
                    get_config_value("MINIMAX_ANTHROPIC_BASE_URL")
                    or "https://api.minimaxi.com/anthropic"
                ),
            )
        api_key = get_config_value("OPENAI_API_KEY")
        if api_key:
            return OpenAINarrativeCurator(**{"api_key": api_key}, model=model)
        return DeterministicNarrativeCurator()
    raise ValueError(
        "narrative_curator_mode must be one of: auto, deterministic, minimax, openai"
    )


def build_candidate_seeds(
    *,
    holdings: list[dict[str, Any]],
    mapping_snapshot: dict[str, Any],
    source_catalog: dict[str, Any],
    fund_exposure_tags: list[dict[str, Any]] | None = None,
    registry_snapshot: dict[str, Any],
    as_of_date: str,
) -> dict[str, Any]:
    registry_terms = _registry_terms(registry_snapshot.get("narratives") or [])
    opportunity_codes = {
        str(item.get("stock_code") or "")
        for item in mapping_snapshot.get("unmapped_holdings") or []
        if item.get("stock_code")
    }
    opportunity_codes.update(
        str(item.get("stock_code") or "")
        for item in mapping_snapshot.get("mappings") or []
        if _is_low_confidence_mapping(item)
    )
    source_items = source_catalog.get("items") or []
    company_facts = source_catalog.get("company_facts") or []
    source_items_by_stock: dict[str, list[dict[str, Any]]] = {}
    for item in source_items:
        stock_code = str(item.get("stock_code") or "")
        if not stock_code:
            continue
        source_items_by_stock.setdefault(stock_code, []).append(item)
    company_facts_by_stock: dict[str, list[dict[str, Any]]] = {}
    for fact in company_facts:
        stock_code = str(fact.get("stock_code") or "")
        if not stock_code:
            continue
        company_facts_by_stock.setdefault(stock_code, []).append(fact)
    company_facts_by_id = {
        str(fact.get("company_fact_id") or ""): fact
        for fact in company_facts
        if fact.get("company_fact_id")
    }
    holdings_by_stock = {
        str(holding.get("stock_code") or ""): holding for holding in holdings
    }
    raw_seeds = _cluster_seeds_from_exposure_tags(
        fund_exposure_tags=fund_exposure_tags or [],
        company_facts_by_id=company_facts_by_id,
        as_of_date=as_of_date,
    )
    clustered_stock_codes = {
        str(stock_code)
        for seed in raw_seeds
        for stock_code in seed.get("triggering_stock_codes") or []
        if str(stock_code).strip()
    }
    for stock_code in sorted(code for code in opportunity_codes if code):
        if stock_code in clustered_stock_codes:
            continue
        holding = holdings_by_stock.get(stock_code)
        if holding is None:
            continue
        supporting_items = source_items_by_stock.get(stock_code, [])
        supporting_facts = company_facts_by_stock.get(stock_code, [])
        support_count = len(supporting_facts) or len(supporting_items)
        if support_count < _MIN_SUPPORTING_ITEMS:
            continue
        ranked_terms = _rank_seed_terms(
            holding=holding,
            source_items=supporting_items,
            company_facts=supporting_facts,
            registry_terms=registry_terms,
        )
        if len(ranked_terms) < _MIN_DISTINCT_TERMS:
            continue
        raw_seeds.append(
            {
                "seed_id": _seed_id(stock_code, ranked_terms),
                "seed_type": "holding_source_cluster",
                "triggering_stock_codes": [stock_code],
                "related_exclusion_ids": [],
                "supporting_source_item_ids": [
                    str(item.get("source_item_id")) for item in supporting_items[:6]
                ],
                "supporting_company_fact_ids": [
                    str(fact.get("company_fact_id")) for fact in supporting_facts[:6]
                ],
                "supporting_source_types": sorted(
                    {
                        str(item.get("source_type"))
                        for item in supporting_items
                        if item.get("source_type")
                    }
                ),
                "supporting_fact_types": sorted(
                    {
                        str(fact.get("fact_type"))
                        for fact in supporting_facts
                        if fact.get("fact_type")
                    }
                ),
                "key_terms": [term["display"] for term in ranked_terms[:3]],
                "term_signature": [term["normalized"] for term in ranked_terms[:2]],
                "supporting_item_count": support_count,
                "distinct_source_type_count": len(
                    {
                        str(item.get("source_type"))
                        for item in supporting_items
                        if item.get("source_type")
                    }
                ),
                "seed_rationale": (
                    f"Unmapped or low-confidence holding {stock_code} repeated "
                    f"terms {', '.join(term['display'] for term in ranked_terms[:3])} "
                    f"across {len(supporting_items)} source items."
                ),
                "first_seen_at": as_of_date,
            }
        )
    merged_seeds = _merge_seeds(raw_seeds)
    return {
        "version": CANDIDATE_SEED_VERSION,
        "items": merged_seeds,
        "summary": {
            "seed_count": len(merged_seeds),
            "opportunity_stock_count": len([code for code in opportunity_codes if code]),
        },
    }


def build_generated_candidates(
    *,
    candidate_seeds: dict[str, Any],
    source_catalog: dict[str, Any],
    holdings: list[dict[str, Any]],
    curator: NarrativeCurator,
) -> dict[str, Any]:
    items_by_id = {
        str(item.get("source_item_id")): item
        for item in source_catalog.get("items") or []
        if item.get("source_item_id")
    }
    holdings_by_stock = {
        str(holding.get("stock_code") or ""): holding for holding in holdings
    }
    candidates = []
    failures = []
    for seed in candidate_seeds.get("items") or []:
        support_items = [
            items_by_id[item_id]
            for item_id in seed.get("supporting_source_item_ids") or []
            if item_id in items_by_id
        ]
        support_holdings = [
            holdings_by_stock[stock_code]
            for stock_code in seed.get("triggering_stock_codes") or []
            if stock_code in holdings_by_stock
        ]
        if not support_items or not support_holdings:
            continue
        if not _seed_supports_candidate_generation(
            seed=seed,
            source_items=support_items,
        ):
            continue
        try:
            candidate = curator.curate_candidate(
                seed=seed,
                source_items=support_items,
                holdings=support_holdings,
            )
        except NarrativeCurationError as exc:
            failures.append(
                {
                    "seed_id": str(seed.get("seed_id") or ""),
                    "seed_type": str(seed.get("seed_type") or ""),
                    "provider_name": exc.provider_name,
                    "provider_version": exc.provider_version,
                    "model": exc.model,
                    "attempt_count": exc.attempt_count,
                    "reason": exc.reason[:500],
                    "triggering_stock_codes": list(seed.get("triggering_stock_codes") or []),
                    "supporting_source_item_ids": list(
                        seed.get("supporting_source_item_ids") or []
                    ),
                }
            )
            continue
        if not _candidate_passes_quality_gate(
            candidate=candidate,
            holdings=support_holdings,
            source_items=support_items,
        ):
            continue
        candidates.append(normalize_candidate_narrative(candidate))
    return {
        "version": GENERATED_CANDIDATE_VERSION,
        "items": _dedupe_candidates(candidates),
        "failures": failures,
        "summary": {
            "generated_candidate_count": len(candidates),
            "failed_candidate_count": len(failures),
            "attempted_seed_count": len(candidate_seeds.get("items") or []),
        },
    }


def _registry_terms(narratives: list[dict[str, Any]]) -> set[str]:
    terms = set()
    for narrative in narratives:
        terms.update(
            normalized_terms(
                [
                    str(narrative.get("name") or ""),
                    str(narrative.get("canonical_taxonomy") or ""),
                    *[str(item) for item in narrative.get("aliases") or []],
                    *[str(item) for item in narrative.get("related_terms") or []],
                ]
            )
        )
    return terms


def _is_low_confidence_mapping(mapping: dict[str, Any]) -> bool:
    confidence = float(mapping.get("confidence", 0))
    return confidence < 0.6 or bool(mapping.get("needs_review"))


def _rank_seed_terms(
    *,
    holding: dict[str, Any],
    source_items: list[dict[str, Any]],
    company_facts: list[dict[str, Any]],
    registry_terms: set[str],
) -> list[dict[str, Any]]:
    display_terms: dict[str, str] = {}
    counter: Counter[str] = Counter()
    stock_name_terms = set(
        normalized_terms(
            [
                str(holding.get("stock_name") or ""),
                str(holding.get("industry") or ""),
                *[
                    str(item.get("stock_name") or "")
                    for item in source_items
                    if item.get("stock_name")
                ],
            ]
        )
    )
    fact_terms = []
    for fact in company_facts:
        if fact.get("is_numeric_only"):
            continue
        fact_terms.extend(fact.get("event_keywords_zh") or [])
        fact_terms.extend(fact.get("event_keywords_en") or [])
        fact_terms.extend(fact.get("company_keywords_zh") or [])
    if fact_terms:
        term_sources = fact_terms
    else:
        term_sources = []
        for item in source_items:
            if item.get("source_type") in {"market_quote", "valuation_snapshot"}:
                continue
            term_sources.extend(item.get("terms") or [])
    for term in term_sources:
        for normalized in normalized_terms([str(term)]):
            if normalized in registry_terms or normalized in stock_name_terms:
                continue
            counter[normalized] += 1
            display_terms.setdefault(normalized, str(term))
    ranked = [
        {
            "normalized": normalized,
            "display": display_terms[normalized],
            "count": count,
        }
        for normalized, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if count >= 2
    ]
    return ranked


def _merge_seeds(raw_seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_signature: dict[tuple[str, ...], dict[str, Any]] = {}
    for seed in raw_seeds:
        signature = tuple(seed.get("term_signature") or ())
        if signature not in by_signature:
            by_signature[signature] = deepcopy(seed)
            continue
        current = by_signature[signature]
        current["triggering_stock_codes"] = sorted(
            {
                *current.get("triggering_stock_codes", []),
                *seed.get("triggering_stock_codes", []),
            }
        )
        current["supporting_source_item_ids"] = sorted(
            {
                *current.get("supporting_source_item_ids", []),
                *seed.get("supporting_source_item_ids", []),
            }
        )
        current["supporting_company_fact_ids"] = sorted(
            {
                *current.get("supporting_company_fact_ids", []),
                *seed.get("supporting_company_fact_ids", []),
            }
        )
        current["supporting_source_types"] = sorted(
            {
                *current.get("supporting_source_types", []),
                *seed.get("supporting_source_types", []),
            }
        )
        current["supporting_fact_types"] = sorted(
            {
                *current.get("supporting_fact_types", []),
                *seed.get("supporting_fact_types", []),
            }
        )
        current["supporting_item_count"] = max(
            len(current["supporting_company_fact_ids"]),
            len(current["supporting_source_item_ids"]),
        )
        current["distinct_source_type_count"] = len(current["supporting_source_types"])
        current["seed_rationale"] = (
            f"Merged seed across {len(current['triggering_stock_codes'])} holding(s) "
            f"with terms {', '.join(current.get('key_terms', []))}."
        )
    return sorted(
        by_signature.values(),
        key=lambda item: (
            -int(item.get("supporting_item_count") or 0),
            tuple(item.get("triggering_stock_codes") or []),
        ),
    )


def _cluster_seeds_from_exposure_tags(
    *,
    fund_exposure_tags: list[dict[str, Any]],
    company_facts_by_id: dict[str, dict[str, Any]],
    as_of_date: str,
) -> list[dict[str, Any]]:
    seeds = []
    for tag in fund_exposure_tags:
        stock_codes = sorted(
            str(item) for item in tag.get("stock_codes") or [] if str(item).strip()
        )
        if len(stock_codes) < 2 or tag.get("linked_narrative_ids"):
            continue
        tag_name_zh = str(tag.get("tag_name_zh") or "").strip()
        normalized_tag_terms = normalized_terms([tag_name_zh])
        if not tag_name_zh or not normalized_tag_terms:
            continue
        supporting_fact_ids = sorted(
            str(item)
            for item in tag.get("supporting_company_fact_ids") or []
            if str(item).strip()
        )
        if not supporting_fact_ids:
            continue
        supporting_source_item_ids = sorted(
            {
                str(source_item_id)
                for fact_id in supporting_fact_ids
                for source_item_id in (
                    company_facts_by_id.get(fact_id, {}).get("supporting_source_item_ids")
                    or []
                )
                if str(source_item_id).strip()
            }
        )
        supporting_fact_types = sorted(
            {
                str(company_facts_by_id.get(fact_id, {}).get("fact_type") or "")
                for fact_id in supporting_fact_ids
                if company_facts_by_id.get(fact_id, {}).get("fact_type")
            }
        )
        supporting_source_types = sorted(
            {
                str(company_facts_by_id.get(fact_id, {}).get("source_type") or "")
                for fact_id in supporting_fact_ids
                if company_facts_by_id.get(fact_id, {}).get("source_type")
            }
        )
        seeds.append(
            {
                "seed_id": _seed_id(
                    "|".join(stock_codes),
                    [
                        {
                            "normalized": normalized_tag_terms[0],
                            "display": tag_name_zh,
                            "count": len(stock_codes),
                        }
                    ],
                ),
                "seed_type": "exposure_tag_cluster",
                "triggering_stock_codes": stock_codes,
                "related_exclusion_ids": [],
                "supporting_source_item_ids": supporting_source_item_ids,
                "supporting_company_fact_ids": supporting_fact_ids,
                "supporting_source_types": supporting_source_types,
                "supporting_fact_types": supporting_fact_types,
                "key_terms": [tag_name_zh],
                "term_signature": [normalized_tag_terms[0]],
                "supporting_item_count": max(
                    len(supporting_fact_ids),
                    len(supporting_source_item_ids),
                ),
                "distinct_source_type_count": len(supporting_source_types),
                "seed_rationale": (
                    f"Cross-stock exposure tag cluster for {tag_name_zh} across "
                    f"{len(stock_codes)} holdings."
                ),
                "first_seen_at": as_of_date,
            }
        )
    return seeds


def _seed_id(stock_code: str, ranked_terms: list[dict[str, Any]]) -> str:
    signature = "|".join(term["normalized"] for term in ranked_terms[:3])
    digest = hashlib.sha256(f"{stock_code}|{signature}".encode("utf-8")).hexdigest()[:12]
    return f"SEED_{digest}".upper()


def _candidate_narrative_id(seed: dict[str, Any]) -> str:
    signature = "|".join(str(term) for term in seed.get("key_terms") or [])
    digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:10]
    return f"C_AUTO_{digest}".upper()


def _aliases(candidate_name: str, key_terms: list[str]) -> list[str]:
    aliases = []
    if not _contains_cjk(candidate_name):
        aliases.append(candidate_name.lower())
    aliases.extend(term for term in key_terms if term != candidate_name)
    deduped = []
    seen = set()
    for item in aliases:
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped[:6]


def _aliases_zh(
    canonical_name_zh: str,
    key_terms: list[str],
    holding_names_zh: list[str],
) -> list[str]:
    return _dedupe_strings(
        [
            canonical_name_zh,
            *[term for term in key_terms if _contains_cjk(term)],
            *holding_names_zh[:2],
        ]
    )[:6]


def _definition(
    candidate_name: str,
    key_terms: list[str],
    industries: list[str],
    holdings: list[dict[str, Any]],
) -> str:
    stock_names = ", ".join(
        str(holding.get("stock_name") or "") for holding in holdings[:3]
    ).strip(", ")
    industry_text = ", ".join(industries) or "the relevant industry"
    term_text = ", ".join(key_terms) or candidate_name
    return (
        f"{candidate_name} refers to a recurring market theme inferred from "
        f"{industry_text} holdings, centered on {term_text}. Current candidate "
        f"support comes from holdings such as {stock_names or 'the triggering holdings'}."
    )


def _inclusion_criteria(
    key_terms: list[str],
    holdings: list[dict[str, Any]],
) -> list[str]:
    stock_names = [
        str(holding.get("stock_name") or "") for holding in holdings if holding.get("stock_name")
    ]
    criteria = [
        f"Company evidence repeatedly references {term}."
        for term in key_terms[:3]
    ]
    if stock_names:
        criteria.append(
            f"Current triggering holdings include {', '.join(stock_names[:3])}."
        )
    return criteria[:4]


def _exclusion_criteria(industries: list[str]) -> list[str]:
    industry_text = ", ".join(industries) or "the same industry"
    return [
        f"Do not use for broad {industry_text} exposure without repeated source support.",
        "Do not promote if evidence is limited to one source item or one-off headlines.",
    ]


def _holding_names_zh(holdings: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(item.get("stock_name") or "")
            for item in holdings
            if item.get("stock_name") and _contains_cjk(str(item.get("stock_name") or ""))
        }
    )


def _candidate_name_zh(
    *,
    key_terms: list[str],
    holdings: list[dict[str, Any]],
    fallback_name: str,
) -> str:
    cjk_terms = [term for term in key_terms if _contains_cjk(term)]
    if cjk_terms:
        return "、".join(cjk_terms[:2])
    industries = [
        str(holding.get("industry") or "")
        for holding in holdings
        if holding.get("industry")
    ]
    if industries and any(_contains_cjk(item) for item in industries):
        return f"{industries[0]}候选主题"
    return fallback_name


def _taxonomy_zh(*, industries: list[str], fallback: str) -> str:
    for industry in industries:
        if _contains_cjk(industry):
            return industry
    return fallback


def _related_terms_zh(key_terms: list[str], holdings: list[dict[str, Any]]) -> list[str]:
    return _dedupe_strings(
        [
            *[term for term in key_terms if _contains_cjk(term)],
            *[
                str(holding.get("industry") or "")
                for holding in holdings
                if holding.get("industry")
                and _contains_cjk(str(holding.get("industry") or ""))
            ],
        ]
    )[:6]


def _definition_zh(
    *,
    candidate_name: str,
    key_terms: list[str],
    industries: list[str],
    holdings: list[dict[str, Any]],
) -> str:
    stock_names = "、".join(_holding_names_zh(holdings)[:3]) or "触发持仓"
    cjk_terms = [term for term in key_terms if _contains_cjk(term)]
    term_text = "、".join(cjk_terms[:3]) or candidate_name
    industry_text = next((item for item in industries if _contains_cjk(item)), "相关行业")
    return (
        f"{candidate_name}是一个基于{industry_text}持仓抽象出的候选主题，"
        f"当前由{stock_names}等持仓及{term_text}相关证据共同触发。"
    )


def _inclusion_criteria_zh(
    key_terms: list[str],
    holdings: list[dict[str, Any]],
) -> list[str]:
    criteria = [
        f"相关证据反复出现“{term}”线索。"
        for term in key_terms[:3]
        if _contains_cjk(term)
    ]
    holding_names = _holding_names_zh(holdings)
    if holding_names:
        criteria.append(f"核心触发持仓包括{'、'.join(holding_names[:3])}。")
    return criteria[:4] or ["需要多条中文证据共同支撑该候选主题。"]


def _exclusion_criteria_zh(industries: list[str]) -> list[str]:
    industry_text = next((item for item in industries if _contains_cjk(item)), "相关行业")
    return [
        f"不能仅凭单一{industry_text}行业标签就提升为正式主题。",
        "不能仅凭一次性公告、单日行情或单条估值快照就提升为正式主题。",
    ]


def _why_not_company_event_zh(
    seed: dict[str, Any],
    holdings: list[dict[str, Any]],
) -> str:
    stock_count = len(seed.get("triggering_stock_codes") or [])
    holding_names = _holding_names_zh(holdings)
    if stock_count >= 2:
        return f"该候选由{stock_count}只持仓共同触发，不是单一公司的孤立事件。"
    if holding_names:
        return (
            f"该候选目前主要由{'、'.join(holding_names[:2])}相关线索触发，"
            "只有在后续出现跨公司共性证据时才适合提升为正式主题。"
        )
    return "该候选需要跨公司共性证据，不能直接视为单家公司事件。"


def _dedupe_strings(items: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _citation_from_source_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": item.get("source_item_id"),
        "source_type": item.get("source_type"),
        "stock_code": item.get("stock_code"),
        "stock_name": item.get("stock_name"),
        "event_date": item.get("event_date"),
        "title": item.get("title"),
        "source_url": item.get("source_url"),
        "provider_name": item.get("provider_name"),
    }


def _curation_citations(
    *,
    requested_ids: list[str],
    fallback_citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not requested_ids:
        return fallback_citations
    citations_by_id = {
        str(item.get("source_item_id")): item for item in fallback_citations
    }
    return [
        citations_by_id[item_id]
        for item_id in requested_ids
        if item_id in citations_by_id
    ] or fallback_citations


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_narrative_id") or "")
        if not candidate_id:
            continue
        if candidate_id not in deduped:
            deduped[candidate_id] = candidate
            continue
        current = deduped[candidate_id]
        current["triggering_stock_codes"] = sorted(
            {
                *current.get("triggering_stock_codes", []),
                *candidate.get("triggering_stock_codes", []),
            }
        )
        current["representative_citations"] = [
            *current.get("representative_citations", []),
            *candidate.get("representative_citations", []),
        ][:3]
    return list(deduped.values())


def _seed_supports_candidate_generation(
    *,
    seed: dict[str, Any],
    source_items: list[dict[str, Any]],
) -> bool:
    triggering_stock_codes = list(seed.get("triggering_stock_codes") or [])
    if len(triggering_stock_codes) >= 2:
        return True
    source_types = {
        str(item.get("source_type") or "")
        for item in source_items
        if item.get("source_type")
    }
    if source_types & {"announcement", "evidence"}:
        return True
    key_terms = list(seed.get("key_terms") or [])
    return any(_contains_cjk(term) for term in key_terms)


def _candidate_passes_quality_gate(
    *,
    candidate: dict[str, Any],
    holdings: list[dict[str, Any]],
    source_items: list[dict[str, Any]],
) -> bool:
    candidate_name = str(candidate.get("name") or "").strip()
    if not candidate_name:
        return False
    triggering_stock_count = len(
        [stock_code for stock_code in candidate.get("triggering_stock_codes") or [] if stock_code]
    )
    source_types = {
        str(item.get("source_type") or "")
        for item in source_items
        if item.get("source_type")
    }
    if triggering_stock_count < 2 and not (source_types & {"announcement", "evidence"}):
        return False
    company_terms = set(
        normalized_terms(
            [
                *[
                    str(holding.get("stock_name") or "")
                    for holding in holdings
                    if holding.get("stock_name")
                ],
                *[
                    str(item.get("stock_name") or "")
                    for item in source_items
                    if item.get("stock_name")
                ],
            ]
        )
    )
    candidate_name_terms = set(normalized_terms([candidate_name]))
    if candidate_name_terms and candidate_name_terms <= company_terms:
        return False
    if not _contains_cjk(candidate_name) and not (source_types & {"announcement", "evidence"}):
        return False
    return True


def _fallback_candidate(
    fallback: dict[str, Any],
    *,
    requested_provider: str,
    requested_version: str,
    model: str,
    reason: str,
) -> dict[str, Any]:
    return {
        **fallback,
        "derivation": {
            **deepcopy(fallback["derivation"]),
            "requested_curation_provider": requested_provider,
            "requested_curation_provider_version": requested_version,
            "requested_model": model,
            "curation_fallback_reason": reason[:500],
        },
    }


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _today_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _minimax_system_prompt() -> str:
    return (
        "You curate candidate market narratives for a China A-share investment research system. "
        "Narrative names, definitions, rationale, and criteria must be in Chinese. "
        "A narrative must be an abstract market theme, not a company name, brand name, province name, "
        "or a direct restatement of one stock's identity. Ignore parsing artifacts such as 'for', "
        "'ltd', 'co', or templated quote/valuation wording. "
        "Only use provided facts. Do not invent URLs, dates, cited items, stock codes, or numbers. "
        "Return one JSON object only with keys: "
        "name, canonical_taxonomy, aliases, related_terms, rationale, definition, "
        "inclusion_criteria, exclusion_criteria, confidence, representative_citation_ids."
    )


def _curation_request_payload(
    *,
    seed: dict[str, Any],
    holdings: list[dict[str, Any]],
    source_items: list[dict[str, Any]],
    fallback: dict[str, Any],
) -> str:
    return json.dumps(
        {
            "seed": seed,
            "holdings": holdings,
            "source_items": source_items,
            "fallback_candidate": fallback,
        },
        ensure_ascii=False,
    )


def _candidate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "canonical_taxonomy": {"type": "string"},
            "aliases": {"type": "array", "items": {"type": "string"}},
            "related_terms": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
            "definition": {"type": "string"},
            "inclusion_criteria": {"type": "array", "items": {"type": "string"}},
            "exclusion_criteria": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
            "representative_citation_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "name",
            "canonical_taxonomy",
            "aliases",
            "related_terms",
            "rationale",
            "definition",
            "inclusion_criteria",
            "exclusion_criteria",
            "confidence",
            "representative_citation_ids",
        ],
    }


def _post_json(
    *,
    url: str,
    api_key: str,
    body: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"OpenAI narrative curation failed: {detail}") from exc


def _response_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for output in payload.get("output") or []:
        if not isinstance(output, dict):
            continue
        for content in output.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ValueError("OpenAI narrative curation response missing output_text")


def _anthropic_message_text(message: Any) -> str:
    blocks = getattr(message, "content", None)
    if not isinstance(blocks, list):
        raise ValueError("MiniMax narrative curation response missing content blocks")
    texts = []
    for block in blocks:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str) and text.strip():
                texts.append(text)
    if not texts:
        raise ValueError("MiniMax narrative curation response missing text block")
    return "\n".join(texts)


def _minimax_failure_reason(*, exc: Exception, message: Any | None) -> str:
    parts = [str(exc)]
    if message is None:
        return "; ".join(parts)
    stop_reason = getattr(message, "stop_reason", None)
    if stop_reason:
        parts.append(f"stop_reason={stop_reason}")
    try:
        text = _anthropic_message_text(message).strip()
    except Exception:
        text = ""
    if text:
        excerpt = text.replace("\n", " ")[:180]
        parts.append(f"text_excerpt={excerpt}")
    return "; ".join(parts)


def _parse_json_text(text: str) -> dict[str, Any]:
    normalized = text.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()
        if normalized.lower().startswith("json"):
            normalized = normalized[4:].strip()
    if normalized and not normalized.startswith("{"):
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start >= 0 and end > start:
            normalized = normalized[start : end + 1]
    payload = json.loads(normalized)
    if not isinstance(payload, dict):
        raise ValueError("Narrative curation response must decode to a JSON object")
    return payload
