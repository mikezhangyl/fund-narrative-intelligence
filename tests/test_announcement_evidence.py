from src.modules.evidence.announcements import convert_announcements_to_evidence
from src.validation import validate_evidence_payload


def test_converts_supporting_cninfo_announcement_to_mapped_evidence():
    announcements_payload = {
        "version": "cninfo-announcement-v1",
        "data_quality": "fresh",
        "announcements": [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "2026年度业绩预增公告",
                "category": "业绩预告",
                "announcement_date": "2026-05-12",
                "source": "cninfo",
                "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
            }
        ],
        "missing_stock_codes": [],
    }
    mappings = [
        {
            "stock_code": "000001",
            "narrative_id": "N_BAIJIU_CONSUMPTION",
            "mapping_weight": 0.7,
            "confidence": 0.8,
            "method": "fixture",
        }
    ]

    result = convert_announcements_to_evidence(
        announcements_payload=announcements_payload,
        stock_mappings=mappings,
        as_of_date="2026-05-13",
    )

    assert result["version"] == "announcement-evidence-v1"
    assert result["data_quality"] == "fresh"
    assert result["unmapped_stock_codes"] == []
    assert result["skipped_announcement_count"] == 0
    assert len(result["evidence"]) == 1
    evidence = result["evidence"][0]
    assert evidence["evidence_id"].startswith("EV_ANN_000001_N_BAIJIU_CONSUMPTION_")
    assert evidence["narrative_id"] == "N_BAIJIU_CONSUMPTION"
    assert evidence["type"] == "earnings"
    assert evidence["source"] == "cninfo_announcement"
    assert evidence["source_url"] == "https://static.cninfo.com.cn/finalpage/1.PDF"
    assert evidence["title"] == "2026年度业绩预增公告"
    assert evidence["sentiment"] == "positive"
    assert evidence["confidence"] == 0.552
    assert evidence["event_date"] == "2026-05-12"
    assert evidence["stock_code"] == "000001"
    assert evidence["provider_data_quality"] == "fresh"
    validate_evidence_payload({"version": result["version"], "evidence": result["evidence"]})


def test_converts_risk_announcement_to_negative_evidence_and_cleans_title():
    announcements_payload = {
        "version": "cninfo-announcement-v1",
        "data_quality": "partial",
        "announcements": [
            {
                "stock_code": "300750",
                "stock_name": "宁德时代",
                "title": "<em>重大诉讼及风险提示公告</em>",
                "category": "风险提示",
                "announcement_date": "2026-05-09",
                "source": "cninfo",
                "source_url": None,
            }
        ],
        "missing_stock_codes": ["000001"],
    }
    mappings = [
        {
            "stock_code": "300750",
            "narrative_id": "N_NEW_ENERGY_EQUIPMENT",
            "mapping_weight": 0.9,
            "confidence": 0.75,
            "method": "fixture",
        }
    ]

    result = convert_announcements_to_evidence(
        announcements_payload=announcements_payload,
        stock_mappings=mappings,
        as_of_date="2026-05-13",
    )

    assert result["data_quality"] == "partial"
    assert result["missing_stock_codes"] == ["000001"]
    assert result["evidence"][0]["type"] == "risk"
    assert result["evidence"][0]["sentiment"] == "negative"
    assert result["evidence"][0]["title"] == "重大诉讼及风险提示公告"
    assert result["evidence"][0]["confidence"] == 0.405
    assert "partial-quality CNINFO announcement metadata" in result["evidence"][0]["summary"]


def test_maps_one_announcement_to_each_stock_narrative_mapping():
    announcements_payload = {
        "version": "cninfo-announcement-v1",
        "data_quality": "fresh",
        "announcements": [
            {
                "stock_code": "688981",
                "stock_name": "中芯国际",
                "title": "签署重大设备订单合同公告",
                "category": "重大合同",
                "announcement_date": "2026-05-11",
                "source": "cninfo",
                "source_url": "https://static.cninfo.com.cn/finalpage/2.PDF",
            }
        ],
        "missing_stock_codes": [],
    }
    mappings = [
        {
            "stock_code": "688981",
            "narrative_id": "N_SEMI_CAPEX",
            "mapping_weight": 0.8,
            "confidence": 0.82,
            "method": "fixture",
        },
        {
            "stock_code": "688981",
            "narrative_id": "N_AI_INFRA",
            "mapping_weight": 0.2,
            "confidence": 0.7,
            "method": "fixture",
        },
    ]

    result = convert_announcements_to_evidence(
        announcements_payload=announcements_payload,
        stock_mappings=mappings,
        as_of_date="2026-05-13",
    )

    assert [item["narrative_id"] for item in result["evidence"]] == [
        "N_AI_INFRA",
        "N_SEMI_CAPEX",
    ]
    assert all(item["type"] == "orders" for item in result["evidence"])
    assert all(item["sentiment"] == "positive" for item in result["evidence"])


def test_tracks_unmapped_and_skipped_announcements_without_crashing():
    announcements_payload = {
        "version": "cninfo-announcement-v1",
        "data_quality": "fresh",
        "announcements": [
            {
                "stock_code": "000999",
                "stock_name": "未映射公司",
                "title": "董事会决议公告",
                "category": "董事会",
                "announcement_date": "bad-date",
                "source": "cninfo",
                "source_url": None,
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "",
                "category": "公告",
                "announcement_date": "2026-05-13",
                "source": "cninfo",
                "source_url": None,
            },
        ],
        "missing_stock_codes": [],
    }

    result = convert_announcements_to_evidence(
        announcements_payload=announcements_payload,
        stock_mappings=[],
        as_of_date="2026-05-13",
    )

    assert result["evidence"] == []
    assert result["unmapped_stock_codes"] == ["000999"]
    assert result["skipped_announcement_count"] == 1


def test_classifies_capital_financial_governance_and_generic_announcements():
    announcements_payload = {
        "version": "cninfo-announcement-v1",
        "data_quality": "fresh",
        "announcements": [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "股份回购进展公告",
                "category": "回购",
                "announcement_date": "2026-05-10",
                "source": "cninfo",
                "source_url": None,
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "2026年半年度报告",
                "category": "定期报告",
                "announcement_date": "2026-05-11",
                "source": "cninfo",
                "source_url": None,
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "董事会决议公告",
                "category": "董事会",
                "announcement_date": "2026-05-12",
                "source": "cninfo",
                "source_url": None,
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "关于召开说明会的公告",
                "category": "公告",
                "announcement_date": "2026-05-13",
                "source": "cninfo",
                "source_url": None,
            },
        ],
        "missing_stock_codes": [],
    }
    mappings = [
        {
            "stock_code": "000001",
            "narrative_id": "N_BANK_STABILITY",
            "mapping_weight": 1.0,
            "confidence": 1.0,
            "method": "fixture",
        }
    ]

    result = convert_announcements_to_evidence(
        announcements_payload=announcements_payload,
        stock_mappings=mappings,
        as_of_date="2026-05-13",
    )

    assert [(item["type"], item["sentiment"]) for item in result["evidence"]] == [
        ("capital_flow", "positive"),
        ("financial_report", "mixed"),
        ("governance", "mixed"),
        ("announcement", "mixed"),
    ]
