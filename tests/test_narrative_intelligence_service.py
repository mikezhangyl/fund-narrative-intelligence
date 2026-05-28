import json
from types import SimpleNamespace

from src.modules.narrative_intelligence import (
    candidate_generation as candidate_generation_module,
)
from src.modules.narrative_intelligence import service as narrative_service_module
from src.modules.narrative_intelligence.service import NarrativeIntelligenceService
from src.modules.narrative_intelligence.source_scout import build_source_catalog
from src.orchestrator import run_pipeline
from src.providers import eastmoney as eastmoney_module


def test_service_builds_context_and_diagnostics_for_first_slice():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "600001",
                "stock_name": "测试电子",
                "industry": "电子",
                "weight": 0.12,
            },
            {
                "stock_code": "600002",
                "stock_name": "平台软件",
                "industry": "软件",
                "weight": 0.08,
            },
            {
                "stock_code": "600003",
                "stock_name": "云基础设施",
                "industry": "云计算",
                "weight": 0.05,
            },
        ],
        registry_payload={
            "version": "registry-v1",
            "narratives": [
                {
                    "narrative_id": "N_HARDWARE",
                    "name": "Electronics Hardware",
                    "canonical_taxonomy": "Technology",
                    "parent_id": None,
                    "level": 1,
                    "status": "active",
                    "aliases": [],
                    "related_terms": ["电子"],
                    "human_review_status": "approved",
                    "reviewed_by": "seed",
                    "reviewed_at": "2026-05-15T00:00:00+00:00",
                    "first_seen_at": "2026-05-01",
                    "last_updated_at": "2026-05-15",
                },
                {
                    "narrative_id": "N_SOFTWARE",
                    "name": "Platform Software",
                    "canonical_taxonomy": "Technology",
                    "parent_id": None,
                    "level": 1,
                    "status": "active",
                    "aliases": [],
                    "related_terms": ["软件"],
                    "human_review_status": "approved",
                    "reviewed_by": "seed",
                    "reviewed_at": "2026-05-15T00:00:00+00:00",
                    "first_seen_at": "2026-05-01",
                    "last_updated_at": "2026-05-15",
                },
                {
                    "narrative_id": "N_CLOUD",
                    "name": "Cloud Infrastructure",
                    "canonical_taxonomy": "Technology",
                    "parent_id": None,
                    "level": 1,
                    "status": "active",
                    "aliases": [],
                    "related_terms": ["云"],
                    "human_review_status": "approved",
                    "reviewed_by": "seed",
                    "reviewed_at": "2026-05-15T00:00:00+00:00",
                    "first_seen_at": "2026-05-01",
                    "last_updated_at": "2026-05-15",
                },
            ],
            "candidate_narratives": [
                {
                    "candidate_narrative_id": "C_CONSUMER_DEVICE_EXPORTS",
                    "name": "Consumer Device Exports",
                    "canonical_taxonomy": "Technology Hardware",
                    "status": "candidate",
                    "source": "mapping_exclusion_review",
                    "triggering_stock_codes": ["600001"],
                    "related_exclusion_ids": ["EX_HARDWARE_600001"],
                    "aliases": [],
                    "related_terms": ["出海硬件"],
                    "rationale": "The holding looks like device exposure, not hardware-cycle exposure.",
                    "human_review_status": "candidate",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "first_seen_at": "2026-05-15",
                    "last_updated_at": "2026-05-15",
                }
            ],
        },
        mappings=[
            {
                "stock_code": "600002",
                "narrative_id": "N_SOFTWARE",
                "mapping_weight": 0.7,
                "confidence": 0.55,
                "method": "fixture_rule",
            },
            {
                "stock_code": "600003",
                "narrative_id": "N_CLOUD",
                "mapping_weight": 0.8,
                "confidence": 0.91,
                "method": "fixture_rule",
            },
        ],
        mapping_exclusions=[
            {
                "exclusion_id": "EX_HARDWARE_600001",
                "stock_code": "600001",
                "narrative_id": "N_HARDWARE",
                "method": "registry_term_rule",
                "reason": "Electronics label is too broad for this hardware-cycle narrative.",
                "recommended_action": "candidate_narrative_review",
            }
        ],
    )

    context = service.build_context()
    snapshot = service.build_snapshot(
        evidence=[
            {
                "evidence_id": "EV_SOFTWARE_POSITIVE",
                "narrative_id": "N_SOFTWARE",
                "sentiment": "positive",
            },
            {
                "evidence_id": "EV_SOFTWARE_NEGATIVE",
                "narrative_id": "N_SOFTWARE",
                "sentiment": "negative",
            },
        ],
        signal_events=[
            {
                "signal_id": "SIG_SOFTWARE",
                "narrative_id": "N_SOFTWARE",
                "signal_type": "guidance_raise",
                "strength": 0.8,
                "confidence": 0.8,
                "confidence_multiplier": 1.0,
                "event_date": "2026-05-15",
                "half_life_days": 45,
            },
            {
                "signal_id": "SIG_CLOUD",
                "narrative_id": "N_CLOUD",
                "signal_type": "institutional_inflow",
                "strength": 0.7,
                "confidence": 0.75,
                "confidence_multiplier": 1.0,
                "event_date": "2026-05-15",
                "half_life_days": 45,
            },
        ],
        as_of_date="2026-05-15",
        data_quality="fresh",
    )

    assert context["registry_snapshot"]["version"] == "registry-v1"
    assert context["mapping_snapshot"]["unmapped_holdings"] == [
        {
            "stock_code": "600001",
            "stock_name": "测试电子",
            "industry": "电子",
            "weight": 0.12,
        }
    ]
    assert context["candidate_narratives"][0]["candidate_narrative_id"] == (
        "C_CONSUMER_DEVICE_EXPORTS"
    )
    assert context["candidate_review_queue"]["summary"] == {
        "total_count": 1,
        "pending_count": 1,
        "action_required": True,
    }
    assert len(snapshot["all_narratives"]) == 2
    assert snapshot["primary_narrative"]["narrative_id"] == "N_SOFTWARE"
    assert snapshot["diagnostics"]["summary"] == {
        "unmapped_holding_count": 1,
        "low_confidence_mapping_count": 1,
        "missing_evidence_narrative_count": 0,
        "conflicting_evidence_narrative_count": 1,
        "action_required": True,
    }
    assert snapshot["diagnostics"]["low_confidence_mappings"] == [
        {
            "stock_code": "600002",
            "stock_name": "平台软件",
            "industry": "软件",
            "weight": 0.08,
            "narrative_id": "N_SOFTWARE",
            "narrative_name": "Platform Software",
            "method": "fixture_rule",
            "confidence": 0.55,
            "mapping_weight": 0.7,
            "needs_review": False,
            "precision_flag": None,
        }
    ]
    assert snapshot["diagnostics"]["missing_evidence_narratives"] == []
    assert snapshot["diagnostics"]["conflicting_evidence_narratives"] == [
        {
            "narrative_id": "N_SOFTWARE",
            "name": "Platform Software",
            "positive_evidence_count": 1,
            "negative_evidence_count": 1,
        }
    ]
    cloud_evidence = next(
        item
        for item in snapshot["narrative_evidence"]["items"]
        if item["narrative_id"] == "N_CLOUD"
    )
    assert cloud_evidence["support_status"] == "limited"
    assert cloud_evidence["direct_evidence_count"] == 0
    assert cloud_evidence["signal_evidence_count"] == 1
    assert snapshot["source_catalog"]["stats"]["item_count"] == 2
    assert snapshot["candidate_seeds"]["summary"]["seed_count"] == 0
    assert snapshot["generated_candidate_narratives"] == []


def test_service_generates_candidate_narratives_from_source_supported_unmapped_holdings():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "700001",
                "stock_name": "PhotonLink",
                "industry": "Communications Infrastructure",
                "weight": 0.11,
            }
        ],
        registry_payload={
            "version": "registry-v1",
            "narratives": [
                {
                    "narrative_id": "N_AI_INFRA",
                    "name": "AI Infrastructure",
                    "canonical_taxonomy": "AI",
                    "parent_id": None,
                    "level": 1,
                    "status": "active",
                    "aliases": [],
                    "related_terms": ["gpu", "datacenter"],
                    "human_review_status": "approved",
                    "reviewed_by": "seed",
                    "reviewed_at": "2026-05-15T00:00:00+00:00",
                    "first_seen_at": "2026-05-01",
                    "last_updated_at": "2026-05-15",
                }
            ],
            "candidate_narratives": [],
        },
        mappings=[],
        mapping_exclusions=[],
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        announcements_payload={
            "version": "announcement-v1",
            "provider_name": "fake-announcements",
            "provider_version": "fake-announcements-v1",
            "data_quality": "fresh",
            "announcements": [
                {
                    "stock_code": "700001",
                    "stock_name": "PhotonLink",
                    "title": "PhotonLink wins optical interconnect order for AI clusters",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source": "exchange",
                    "source_url": "https://example.com/a1",
                },
                {
                    "stock_code": "700001",
                    "stock_name": "PhotonLink",
                    "title": "PhotonLink expands optical interconnect switching platform",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source": "exchange",
                    "source_url": "https://example.com/a2",
                },
            ],
            "missing_stock_codes": [],
        },
    )

    assert snapshot["candidate_seeds"]["summary"]["seed_count"] == 1
    generated = snapshot["generated_candidate_narratives"]
    assert len(generated) == 1
    assert generated[0]["source"] == "narrative_intelligence_generation"
    assert generated[0]["triggering_stock_codes"] == ["700001"]
    assert generated[0]["definition"]
    assert len(generated[0]["representative_citations"]) == 2
    assert snapshot["candidate_review_queue"]["summary"]["total_count"] == 1
    assert snapshot["mapping_proposals"]["summary"]["proposal_count"] == 1
    assert snapshot["mapping_proposals"]["items"][0]["stock_code"] == "700001"
    assert snapshot["source_catalog"]["stats"]["source_type_counts"]["announcement"] == 2


def test_source_catalog_extracts_company_facts_and_numeric_only_flags():
    catalog = build_source_catalog(
        holdings=[
            {
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "industry": "通信设备",
                "weight": 0.1,
            }
        ],
        evidence=[],
        announcements_payload={
            "provider_name": "fake-announcements",
            "provider_version": "fake-announcements-v1",
            "announcements": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创签订高速光模块大单",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source_url": "https://example.com/order",
                }
            ],
        },
        market_quotes_payload={
            "provider_name": "market-quotes",
            "provider_version": "market-quotes-v1",
            "source_url": "https://example.com/quotes",
            "quotes": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "latest_price": 120.3,
                    "change_percent": -5.6,
                    "retrieved_at": "2026-05-15T10:00:00+00:00",
                }
            ],
        },
        valuation_snapshots_payload={
            "provider_name": "valuations",
            "provider_version": "valuations-v1",
            "valuations": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "valuation_pressure": "elevated",
                    "pe_ttm": 55.1,
                    "pb": 8.2,
                    "retrieved_at": "2026-05-15T10:00:00+00:00",
                    "source_url": "https://example.com/valuation",
                }
            ],
        },
        financial_metrics_payload={
            "provider_name": "financial-metrics",
            "provider_version": "financial-metrics-v1",
            "metrics": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "report_type": "一季报",
                    "report_date": "2026-03-31",
                    "revenue_yoy": 38.2,
                    "parent_net_profit_yoy": 44.7,
                    "source_url": "https://example.com/financial",
                }
            ],
        },
    )

    assert catalog["company_fact_stats"] == {
        "fact_count": 4,
        "fact_type_counts": {
            "业绩增长": 1,
            "估值承压": 1,
            "股价回撤": 1,
            "订单进展": 1,
        },
        "fact_direction_counts": {
            "negative": 2,
            "positive": 2,
        },
        "stock_coverage_count": 1,
        "narrative_ready_fact_count": 2,
        "numeric_only_fact_count": 2,
    }
    order_fact = next(
        fact
        for fact in catalog["company_facts"]
        if fact["fact_type"] == "订单进展"
    )
    assert order_fact["fact_direction"] == "positive"
    assert order_fact["narrative_ready"] is True
    assert order_fact["supporting_source_item_ids"]
    assert "中际旭创" in order_fact["fact_summary_zh"]
    quote_fact = next(
        fact
        for fact in catalog["company_facts"]
        if fact["fact_type"] == "股价回撤"
    )
    assert quote_fact["narrative_ready"] is False
    assert quote_fact["is_numeric_only"] is True


def test_service_derives_company_exposure_tags_from_holdings_and_company_facts():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "industry": "通信设备",
                "weight": 0.1,
            }
        ],
        registry_payload={
            "version": "registry-v1",
            "narratives": [],
            "candidate_narratives": [],
        },
        mappings=[],
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        announcements_payload={
            "provider_name": "fake-announcements",
            "provider_version": "fake-announcements-v1",
            "announcements": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创签订高速光模块大单",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source_url": "https://example.com/order",
                },
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创扩充800G光模块产能",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source_url": "https://example.com/expansion",
                },
            ],
        },
    )

    assert snapshot["company_exposure_tag_stats"] == {
        "tag_count": 2,
        "stock_coverage_count": 1,
        "source_counts": {
            "company_fact_keyword": 1,
            "holding_industry": 1,
        },
    }
    assert snapshot["company_exposure_tags"] == [
        {
            "company_exposure_tag_id": "TAG_300308_光模块",
            "stock_code": "300308",
            "stock_name": "中际旭创",
            "tag_name_zh": "光模块",
            "tag_name_en": "Optical Module",
            "tag_source": "company_fact_keyword",
            "tag_confidence": 0.74,
            "supporting_company_fact_ids": [
                *sorted(
                    [
                        snapshot["company_facts"][0]["company_fact_id"],
                        snapshot["company_facts"][1]["company_fact_id"],
                    ]
                ),
            ],
        },
        {
            "company_exposure_tag_id": "TAG_300308_通信设备",
            "stock_code": "300308",
            "stock_name": "中际旭创",
            "tag_name_zh": "通信设备",
            "tag_name_en": "Communication Equipment",
            "tag_source": "holding_industry",
            "tag_confidence": 0.72,
            "supporting_company_fact_ids": [],
        },
    ]


def test_service_aggregates_fund_exposure_tags_and_links_them_to_narratives():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "industry": "通信设备",
                "weight": 0.1,
            }
        ],
        registry_payload={
            "version": "registry-v2",
            "narratives": [
                {
                    "narrative_id": "N_AI_OPTICAL",
                    "name": "AI Optical Interconnect Infrastructure",
                    "canonical_name_zh": "AI光互联基础设施",
                    "display_name": "AI光互联基础设施",
                    "canonical_taxonomy": "AI Infrastructure",
                    "canonical_taxonomy_zh": "人工智能基础设施",
                    "aliases": [],
                    "aliases_zh": ["光互联"],
                    "related_terms": ["optical interconnect"],
                    "related_terms_zh": ["光模块", "CPO"],
                    "status": "active",
                    "human_review_status": "approved",
                    "reviewed_by": "seed",
                    "reviewed_at": "2026-05-15T00:00:00+00:00",
                    "first_seen_at": "2026-05-01",
                    "last_updated_at": "2026-05-15",
                }
            ],
            "candidate_narratives": [],
        },
        mappings=[],
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        announcements_payload={
            "provider_name": "fake-announcements",
            "provider_version": "fake-announcements-v1",
            "announcements": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创签订高速光模块大单",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source_url": "https://example.com/order",
                },
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创扩充800G光模块产能",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source_url": "https://example.com/expansion",
                },
            ],
        },
    )

    assert snapshot["fund_exposure_tag_stats"] == {
        "tag_count": 2,
        "linked_tag_count": 1,
        "stock_coverage_count": 1,
    }
    assert snapshot["fund_exposure_tags"] == [
        {
            "tag_name_zh": "光模块",
            "tag_name_en": "Optical Module",
            "raw_exposure": 0.1,
            "normalized_exposure": 0.5,
            "confidence": 0.74,
            "stock_codes": ["300308"],
            "stock_names": ["中际旭创"],
            "supporting_company_fact_ids": [
                *sorted(
                    [
                        snapshot["company_facts"][0]["company_fact_id"],
                        snapshot["company_facts"][1]["company_fact_id"],
                    ]
                ),
            ],
            "linked_narrative_ids": ["N_AI_OPTICAL"],
            "linked_narrative_names": ["AI光互联基础设施"],
            "link_method": "registry_tag_term_match",
            "link_confidence": 0.78,
        },
        {
            "tag_name_zh": "通信设备",
            "tag_name_en": "Communication Equipment",
            "raw_exposure": 0.1,
            "normalized_exposure": 0.5,
            "confidence": 0.72,
            "stock_codes": ["300308"],
            "stock_names": ["中际旭创"],
            "supporting_company_fact_ids": [],
            "linked_narrative_ids": [],
            "linked_narrative_names": [],
            "link_method": None,
            "link_confidence": None,
        },
    ]


def test_service_builds_cluster_candidate_seed_from_multi_stock_exposure_tag():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "industry": "通信设备",
                "weight": 0.1,
            },
            {
                "stock_code": "300502",
                "stock_name": "新易盛",
                "industry": "通信设备",
                "weight": 0.08,
            },
        ],
        registry_payload={
            "version": "registry-v2",
            "narratives": [],
            "candidate_narratives": [],
        },
        mappings=[],
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        announcements_payload={
            "provider_name": "fake-announcements",
            "provider_version": "fake-announcements-v1",
            "announcements": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创签订高速光模块大单",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source_url": "https://example.com/order-1",
                },
                {
                    "stock_code": "300502",
                    "stock_name": "新易盛",
                    "title": "新易盛扩充800G光模块产能",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source_url": "https://example.com/order-2",
                },
            ],
        },
    )

    assert snapshot["candidate_seeds"]["summary"]["seed_count"] == 1
    assert snapshot["candidate_seeds"]["items"] == [
        {
            "seed_id": snapshot["candidate_seeds"]["items"][0]["seed_id"],
            "seed_type": "exposure_tag_cluster",
            "triggering_stock_codes": ["300308", "300502"],
            "related_exclusion_ids": [],
            "supporting_source_item_ids": [
                snapshot["source_catalog"]["items"][0]["source_item_id"],
                snapshot["source_catalog"]["items"][1]["source_item_id"],
            ],
            "supporting_company_fact_ids": [
                *sorted(
                    [
                        snapshot["company_facts"][0]["company_fact_id"],
                        snapshot["company_facts"][1]["company_fact_id"],
                    ]
                ),
            ],
            "supporting_source_types": ["announcement"],
            "supporting_fact_types": ["产能扩张", "订单进展"],
            "key_terms": ["光模块"],
            "term_signature": ["光模块"],
            "supporting_item_count": 2,
            "distinct_source_type_count": 1,
            "seed_rationale": "Cross-stock exposure tag cluster for 光模块 across 2 holdings.",
            "first_seen_at": "2026-05-15",
        }
    ]
    assert len(snapshot["generated_candidate_narratives"]) == 1
    generated = snapshot["generated_candidate_narratives"][0]
    assert generated["triggering_stock_codes"] == ["300308", "300502"]
    assert generated["canonical_name_zh"] == "光模块"
    assert generated["why_not_company_event_zh"] == (
        "该候选由2只持仓共同触发，不是单一公司的孤立事件。"
    )


def test_service_derives_optical_module_candidate_from_company_name_keywords():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "300502",
                "stock_name": "新易盛",
                "industry": "通信",
                "weight": 0.15,
            },
            {
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "industry": "通信",
                "weight": 0.1366,
            },
        ],
        registry_payload={
            "version": "registry-v2",
            "narratives": [],
            "candidate_narratives": [],
        },
        mappings=[],
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        market_quotes_payload={
            "provider_name": "yahoo-chart",
            "provider_version": "yahoo-chart-v1",
            "quotes": [
                {
                    "stock_code": "300502",
                    "stock_name": "EOPTOLINK TECHNOLOGY INC LTD",
                    "latest_price": 610.05,
                    "change_percent": 8.22,
                    "retrieved_at": "2026-05-15T10:00:00+00:00",
                },
                {
                    "stock_code": "300308",
                    "stock_name": "ZHONGJI INNOLIGHT CO LTD",
                    "latest_price": 1049.87,
                    "change_percent": 11.67,
                    "retrieved_at": "2026-05-15T10:00:00+00:00",
                },
            ],
            "source_url": "multiple://market-quotes",
        },
    )

    assert snapshot["company_exposure_tag_stats"] == {
        "tag_count": 4,
        "stock_coverage_count": 2,
        "source_counts": {
            "company_name_keyword": 2,
            "holding_industry": 2,
        },
    }
    assert any(
        item["tag_name_zh"] == "光模块" and item["tag_source"] == "company_name_keyword"
        for item in snapshot["company_exposure_tags"]
    )
    assert any(
        item["tag_name_zh"] == "光模块"
        and item["stock_codes"] == ["300308", "300502"]
        for item in snapshot["fund_exposure_tags"]
    )
    assert snapshot["candidate_seeds"]["summary"]["seed_count"] == 1
    assert snapshot["generated_candidate_narratives"][0]["canonical_name_zh"] == "光模块"


def test_service_derives_optical_communication_from_chinese_company_names():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "002281",
                "stock_name": "光迅科技",
                "industry": "通信",
                "weight": 0.11,
            },
            {
                "stock_code": "600487",
                "stock_name": "亨通光电",
                "industry": "通信",
                "weight": 0.09,
            },
        ],
        registry_payload={
            "version": "registry-v2",
            "narratives": [],
            "candidate_narratives": [],
        },
        mappings=[],
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        financial_metrics_payload={
            "provider_name": "eastmoney-financial-metrics",
            "provider_version": "eastmoney-financial-metrics-v1",
            "metrics": [
                {
                    "stock_code": "002281",
                    "stock_name": "光迅科技",
                    "report_type": "一季报",
                    "report_date": "2026-03-31",
                    "revenue_yoy": 24.7,
                    "parent_net_profit_yoy": 59.7,
                    "source_url": "https://example.com/002281",
                },
                {
                    "stock_code": "600487",
                    "stock_name": "亨通光电",
                    "report_type": "一季报",
                    "report_date": "2026-03-31",
                    "revenue_yoy": 34.0,
                    "parent_net_profit_yoy": 98.5,
                    "source_url": "https://example.com/600487",
                },
            ],
        },
    )

    assert snapshot["company_exposure_tag_stats"]["source_counts"] == {
        "company_name_keyword": 2,
        "holding_industry": 2,
    }
    assert any(
        item["tag_name_zh"] == "光通信"
        and item["tag_source"] == "company_name_keyword"
        and item["stock_code"] == "002281"
        for item in snapshot["company_exposure_tags"]
    )
    assert any(
        item["tag_name_zh"] == "光通信"
        and item["tag_source"] == "company_name_keyword"
        and item["stock_code"] == "600487"
        for item in snapshot["company_exposure_tags"]
    )
    assert any(
        item["tag_name_zh"] == "光通信"
        and item["stock_codes"] == ["002281", "600487"]
        for item in snapshot["fund_exposure_tags"]
    )
    assert snapshot["generated_candidate_narratives"][0]["canonical_name_zh"] == "光通信"


class FakeAnnouncementProvider:
    provider_name = "fake-announcements"
    provider_version = "fake-announcements-v1"

    def get_announcements(
        self,
        stock_codes: list[str],
        as_of_date: str,
        start_date: str | None = None,
    ) -> dict:
        del as_of_date, start_date
        assert stock_codes == ["777777"]
        return {
            "version": "announcement-v1",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": "fresh",
            "announcements": [
                {
                    "stock_code": "777777",
                    "stock_name": "PhotonLink",
                    "title": "PhotonLink wins optical interconnect order for AI clusters",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source": "exchange",
                    "source_url": "https://example.com/ai-cluster-order",
                },
                {
                    "stock_code": "777777",
                    "stock_name": "PhotonLink",
                    "title": "PhotonLink expands optical interconnect switching platform",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source": "exchange",
                    "source_url": "https://example.com/interconnect-platform",
                },
            ],
            "missing_stock_codes": [],
        }


def test_pipeline_surfaces_narrative_intelligence_diagnostics(tmp_path):
    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())

    assert raw["diagnostics"] == scoring["diagnostics"]
    assert raw["diagnostics"]["version"] == "narrative-intelligence-diagnostics-v1"
    assert raw["diagnostics"]["summary"]["unmapped_holding_count"] == len(
        raw["unmapped_holdings"]
    )
    assert raw["diagnostics"]["summary"]["low_confidence_mapping_count"] == len(
        raw["diagnostics"]["low_confidence_mappings"]
    )
    assert raw["diagnostics"]["summary"]["missing_evidence_narrative_count"] == len(
        raw["diagnostics"]["missing_evidence_narratives"]
    )
    assert raw["diagnostics"]["summary"]["conflicting_evidence_narrative_count"] == len(
        raw["diagnostics"]["conflicting_evidence_narratives"]
    )


def test_pipeline_can_generate_candidate_narratives_and_mapping_proposals(
    tmp_path, monkeypatch
):
    def fake_fetcher(_url: str) -> dict:
        return {
            "Success": True,
            "Expansion": "2026-03-31",
            "Datas": {
                "fundStocks": [
                    {
                        "GPDM": "777777",
                        "GPJC": "PhotonLink",
                        "JZBL": "8.88",
                        "PCTNVCHG": "0",
                        "INDEXNAME": "Communications Infrastructure",
                    }
                ]
            },
        }

    monkeypatch.setattr(eastmoney_module, "_fetch_json", fake_fetcher)

    artifacts = run_pipeline(
        fund_code="161725",
        provider_mode="eastmoney",
        output_dir=tmp_path,
        include_announcement_evidence=True,
        announcement_provider=FakeAnnouncementProvider(),
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    review_queue = json.loads(artifacts["review_queue"].read_text())

    assert raw["candidate_seeds"]["summary"]["seed_count"] == 1
    assert len(raw["generated_candidate_narratives"]) == 1
    generated = raw["generated_candidate_narratives"][0]
    assert generated["triggering_stock_codes"] == ["777777"]
    assert generated["definition"]
    assert generated["representative_citations"][0]["source_url"].startswith(
        "https://example.com/"
    )
    assert raw["candidate_narratives"] == scoring["candidate_narratives"]
    assert review_queue["candidate_narratives"] == scoring["candidate_narratives"]
    assert raw["mapping_proposals"]["summary"]["proposal_count"] == 1
    assert raw["mapping_proposals"]["items"][0]["candidate_narrative_id"] == generated[
        "candidate_narrative_id"
    ]
    assert raw["source_item_stats"]["source_type_counts"]["announcement"] == 2
    assert raw["company_facts"] == scoring["company_facts"]
    assert raw["company_fact_stats"] == {
        "fact_count": 2,
        "fact_type_counts": {"产能扩张": 1, "订单进展": 1},
        "fact_direction_counts": {"positive": 2},
        "stock_coverage_count": 1,
        "narrative_ready_fact_count": 2,
        "numeric_only_fact_count": 0,
    }
    assert raw["company_exposure_tags"] == scoring["company_exposure_tags"]
    assert raw["company_exposure_tag_stats"] == {
        "tag_count": 2,
        "stock_coverage_count": 1,
        "source_counts": {
            "company_fact_keyword": 1,
            "holding_industry": 1,
        },
    }
    assert raw["narrative_generation_enabled"] is True


def test_service_records_candidate_generation_failures_without_fake_fallback(
    monkeypatch,
):
    class FailingCurator:
        def curate_candidate(self, *, seed, source_items, holdings):
            del seed, source_items, holdings
            raise candidate_generation_module.NarrativeCurationError(
                provider_name="minimax-narrative-curator",
                provider_version="anthropic-compatible-v1",
                model="MiniMax-M2.7",
                reason="connection reset after retries",
                attempt_count=3,
            )

    monkeypatch.setattr(
        narrative_service_module,
        "select_narrative_curator",
        lambda mode, *, model: FailingCurator(),
    )

    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "industry": "通信设备",
                "weight": 0.1,
            },
            {
                "stock_code": "300502",
                "stock_name": "新易盛",
                "industry": "通信设备",
                "weight": 0.08,
            },
        ],
        registry_payload={
            "version": "registry-v2",
            "narratives": [],
            "candidate_narratives": [],
        },
        mappings=[],
        enable_narrative_generation=True,
        narrative_curator_mode="minimax",
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        announcements_payload={
            "provider_name": "fake-announcements",
            "provider_version": "fake-announcements-v1",
            "announcements": [
                {
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "title": "中际旭创签订高速光模块大单",
                    "category": "order",
                    "announcement_date": "2026-05-15",
                    "source_url": "https://example.com/order-1",
                },
                {
                    "stock_code": "300502",
                    "stock_name": "新易盛",
                    "title": "新易盛扩充800G光模块产能",
                    "category": "expansion",
                    "announcement_date": "2026-05-14",
                    "source_url": "https://example.com/order-2",
                },
            ],
        },
    )

    assert snapshot["candidate_seeds"]["summary"]["seed_count"] == 1
    assert snapshot["generated_candidate_narratives"] == []
    assert snapshot["candidate_generation_summary"] == {
        "generated_candidate_count": 0,
        "failed_candidate_count": 1,
        "attempted_seed_count": 1,
    }
    assert snapshot["candidate_generation_failures"] == [
        {
            "seed_id": snapshot["candidate_seeds"]["items"][0]["seed_id"],
            "seed_type": "exposure_tag_cluster",
            "provider_name": "minimax-narrative-curator",
            "provider_version": "anthropic-compatible-v1",
            "model": "MiniMax-M2.7",
            "attempt_count": 3,
            "reason": "connection reset after retries",
            "triggering_stock_codes": ["300308", "300502"],
            "supporting_source_item_ids": [
                snapshot["source_catalog"]["items"][0]["source_item_id"],
                snapshot["source_catalog"]["items"][1]["source_item_id"],
            ],
        }
    ]
    assert snapshot["candidate_review_queue"]["summary"]["total_count"] == 0


def test_service_skips_single_stock_numeric_only_candidate_generation():
    service = NarrativeIntelligenceService(
        holdings=[
            {
                "stock_code": "603198",
                "stock_name": "迎驾贡酒",
                "industry": "食品饮料",
                "weight": 0.09,
            }
        ],
        registry_payload={
            "version": "registry-v1",
            "narratives": [
                {
                    "narrative_id": "N_BAIJIU",
                    "name": "白酒消费",
                    "canonical_taxonomy": "消费",
                    "parent_id": None,
                    "level": 1,
                    "status": "active",
                    "aliases": [],
                    "related_terms": ["白酒"],
                    "human_review_status": "approved",
                    "reviewed_by": "seed",
                    "reviewed_at": "2026-05-15T00:00:00+00:00",
                    "first_seen_at": "2026-05-01",
                    "last_updated_at": "2026-05-15",
                }
            ],
            "candidate_narratives": [],
        },
        mappings=[
            {
                "stock_code": "603198",
                "narrative_id": "N_BAIJIU",
                "mapping_weight": 0.8,
                "confidence": 0.45,
                "method": "registry_rule",
                "needs_review": True,
            }
        ],
        enable_narrative_generation=True,
        narrative_curator_mode="deterministic",
    )

    snapshot = service.build_snapshot(
        evidence=[],
        signal_events=[],
        as_of_date="2026-05-15",
        data_quality="fresh",
        market_quotes_payload={
            "provider_name": "yahoo-chart",
            "quotes": [
                {
                    "stock_code": "603198",
                    "stock_name": "ANHUI YINGJIA DISTILLERY CO",
                    "latest_price": 35.27,
                    "change_percent": -7.81,
                    "retrieved_at": "2026-05-15T13:34:42+00:00",
                }
            ],
            "source_url": "multiple://market-quotes",
        },
        valuation_snapshots_payload={
            "provider_name": "quote-derived-valuation",
            "valuations": [
                {
                    "stock_code": "603198",
                    "stock_name": "ANHUI YINGJIA DISTILLERY CO",
                    "valuation_pressure": "discounted",
                    "pe_ttm": None,
                    "pb": None,
                    "retrieved_at": "2026-05-15T13:34:42+00:00",
                    "source_url": "https://example.com/603198",
                }
            ],
        },
        financial_metrics_payload={
            "provider_name": "eastmoney-financial-metrics",
            "metrics": [
                {
                    "stock_code": "603198",
                    "stock_name": "迎驾贡酒",
                    "report_type": "一季报",
                    "report_date": "2026-03-31",
                    "revenue_yoy": 8.91,
                    "parent_net_profit_yoy": 0.73,
                    "source_url": "https://example.com/financial/603198",
                }
            ],
        },
    )

    assert snapshot["candidate_seeds"]["items"] == []
    assert snapshot["generated_candidate_narratives"] == []
    assert snapshot["candidate_review_queue"]["summary"]["total_count"] == 0


def test_select_narrative_curator_auto_prefers_minimax(monkeypatch):
    monkeypatch.setattr(
        candidate_generation_module,
        "get_config_value",
        lambda name: (
            "minimax-key"
            if name == "MINIMAX_API_KEY"
            else "https://api.minimaxi.com/anthropic"
            if name == "MINIMAX_ANTHROPIC_BASE_URL"
            else "openai-key"
            if name == "OPENAI_API_KEY"
            else None
        ),
    )

    curator = candidate_generation_module.select_narrative_curator(
        "auto",
        model="MiniMax-M2.7",
    )

    assert curator.provider_name == "minimax-narrative-curator"


def test_minimax_message_text_uses_text_blocks_only():
    message = SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking="hidden"),
            SimpleNamespace(type="text", text='{"name":"A"}'),
        ]
    )

    assert candidate_generation_module._anthropic_message_text(message) == (
        '{"name":"A"}'
    )


def test_parse_json_text_accepts_markdown_fenced_json():
    payload = candidate_generation_module._parse_json_text(
        '```json\n{"name":"A","confidence":0.7}\n```'
    )

    assert payload == {"name": "A", "confidence": 0.7}


def test_parse_json_text_extracts_embedded_json_object():
    payload = candidate_generation_module._parse_json_text(
        'analysis first\n{"name":"A","confidence":0.7}\ntrailing note'
    )

    assert payload == {"name": "A", "confidence": 0.7}
