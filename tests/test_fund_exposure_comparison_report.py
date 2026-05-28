from __future__ import annotations

import json

from scripts import run_fund_exposure_comparison_report
from src.scanners.fund_exposure_comparison_report import (
    FundExposureComparisonConfig,
    execute_fund_exposure_comparison_report,
    render_html_report,
)


class FakeFundComparisonSource:
    degradation_events = []

    def fetch_fund_profile(self, *, fund_code):
        names = {
            "161725": "招商中证白酒指数",
            "515880": "通信ETF",
            "512760": "芯片ETF",
        }
        return [
            {
                "fund_code": fund_code,
                "fund_name": names.get(fund_code, f"Fund {fund_code}"),
                "fund_type": "index_fund",
                "currency": "CNY",
                "source": "gateway",
            }
        ]

    def fetch_fund_holdings(self, *, fund_code, limit):
        rows_by_fund = {
            "161725": [
                _holding(fund_code, "600519", "贵州茅台", 0.18, "食品饮料"),
                _holding(fund_code, "000858", "五粮液", 0.16, "食品饮料"),
                _holding(fund_code, "000568", "泸州老窖", 0.14, "食品饮料"),
            ],
            "515880": [
                _holding(fund_code, "000063", "中兴通讯", 0.11, "通信"),
                _holding(fund_code, "600519", "贵州茅台", 0.04, "食品饮料"),
                _holding(fund_code, "300308", "中际旭创", 0.09, "通信"),
            ],
            "512760": [
                _holding(fund_code, "688981", "中芯国际", 0.12, "半导体"),
                _holding(fund_code, "600519", "贵州茅台", 0.03, "食品饮料"),
                _holding(fund_code, "300750", "宁德时代", 0.08, "电力设备"),
            ],
        }
        return rows_by_fund[fund_code][:limit]

    def fetch_stock_sector_memberships(self, **kwargs):
        del kwargs
        return []


def _mapping(stock_code: str, narrative_id: str, mapping_weight: float) -> dict:
    return {
        "stock_code": stock_code,
        "narrative_id": narrative_id,
        "mapping_weight": mapping_weight,
        "confidence": 0.8,
        "method": "test_mapping",
    }


NARRATIVE_REGISTRY = {
    "narratives": [
        {"narrative_id": "N_BAIJIU_CONSUMPTION", "display_name": "高端白酒消费"},
        {"narrative_id": "N_COMMUNICATION_EQUIPMENT", "display_name": "通信设备"},
        {"narrative_id": "N_SEMI_CAPEX", "display_name": "半导体景气"},
    ]
}

STOCK_MAPPINGS = [
    _mapping("600519", "N_BAIJIU_CONSUMPTION", 0.9),
    _mapping("000858", "N_BAIJIU_CONSUMPTION", 0.8),
    _mapping("000568", "N_BAIJIU_CONSUMPTION", 0.85),
    _mapping("000063", "N_COMMUNICATION_EQUIPMENT", 0.8),
    _mapping("300308", "N_COMMUNICATION_EQUIPMENT", 0.9),
    _mapping("688981", "N_SEMI_CAPEX", 0.95),
]


def test_execute_fund_exposure_comparison_report_compares_multiple_funds():
    report = execute_fund_exposure_comparison_report(
        data_source=FakeFundComparisonSource(),
        config=FundExposureComparisonConfig(
            fund_codes=("161725", "515880", "512760"),
            limit=10,
        ),
        narrative_registry=NARRATIVE_REGISTRY,
        stock_narrative_mappings=STOCK_MAPPINGS,
    )

    assert report["status"] == "partial"
    assert report["summary"]["fund_count"] == 3
    assert report["summary"]["partial_fund_count"] == 3
    assert report["funds"][0]["fund_code"] == "161725"
    assert report["funds"][0]["concentration"]["top3_weight"] == 0.48
    assert report["holding_overlap_pairs"][0] == {
        "fund_a": "161725",
        "fund_b": "515880",
        "shared_holding_count": 1,
        "shared_symbols": ["600519"],
        "shared_names": ["贵州茅台"],
        "overlap_weight_fund_a": 0.18,
        "overlap_weight_fund_b": 0.04,
    }
    assert report["common_narrative_exposures"] == []
    assert report["differentiating_narrative_exposures"][0]["narrative_name"] == "高端白酒消费"
    assert report["differentiating_narrative_exposures"][0]["dominant_fund"] == "161725"
    assert report["differentiating_narrative_exposures"][0]["raw_exposure_gap"] == 0.382


def test_render_fund_exposure_comparison_html_contains_key_sections():
    report = execute_fund_exposure_comparison_report(
        data_source=FakeFundComparisonSource(),
        config=FundExposureComparisonConfig(fund_codes=("161725", "515880"), limit=10),
        narrative_registry=NARRATIVE_REGISTRY,
        stock_narrative_mappings=STOCK_MAPPINGS,
    )

    html = render_html_report(report)

    assert "<h1>基金暴露横向比较报告</h1>" in html
    assert "招商中证白酒指数" in html
    assert "持仓重合" in html
    assert "差异叙事" in html
    assert "叙事数据来源" in html
    assert "unspecified" in html
    assert "不构成投资建议" in html


def test_fund_exposure_comparison_report_discloses_market_data_source():
    report = execute_fund_exposure_comparison_report(
        data_source=FakeFundComparisonSource(),
        config=FundExposureComparisonConfig(fund_codes=("161725", "515880"), limit=10),
        narrative_registry=NARRATIVE_REGISTRY,
        stock_narrative_mappings=STOCK_MAPPINGS,
        narrative_source={
            "source": "narrative_service",
            "provider": "stock-narrative-service",
            "provider_version": "v0",
            "data_fetch_mode": "narrative_service",
            "warnings": [],
        },
    )

    html = render_html_report(report)

    assert report["narrative_source"]["source"] == "narrative_service"
    assert report["market_data_source"]["status"] == "available"
    assert report["market_data_source"]["source_names"] == ["gateway"]
    assert report["market_data_source"]["warning_count"] == 0
    assert "市场数据来源" in html
    assert "gateway" in html
    assert "无告警" in html


def test_run_fund_exposure_comparison_report_writes_json_and_html(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_fund_exposure_comparison_report,
        "ConsolidatedMarketDataSource",
        lambda: FakeFundComparisonSource(),
    )
    monkeypatch.setattr(
        run_fund_exposure_comparison_report,
        "load_intelligence_context",
        lambda registry_mode, stock_mapping_mode: (NARRATIVE_REGISTRY, STOCK_MAPPINGS),
    )

    exit_code = run_fund_exposure_comparison_report.main(
        [
            "--fund-codes",
            "161725,515880",
            "--limit",
            "10",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "fund_exposure_comparison_report.json").read_text())
    html = (tmp_path / "fund_exposure_comparison_report.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["fund_count"] == 2
    assert payload["summary"]["narrative_source"] == "unspecified"
    assert payload["holding_overlap_pairs"][0]["shared_symbols"] == ["600519"]
    assert "<h1>基金暴露横向比较报告</h1>" in html
    assert "叙事数据来源" in html


def _holding(
    fund_code: str,
    stock_code: str,
    stock_name: str,
    weight: float,
    industry: str,
) -> dict:
    suffix = "SH" if stock_code.startswith("6") else "SZ"
    return {
        "fund_code": fund_code,
        "as_of_date": "2026-03-31",
        "stock_code": stock_code,
        "ts_code": f"{stock_code}.{suffix}",
        "stock_name": stock_name,
        "weight": weight,
        "industry": industry,
        "source": "gateway",
    }
