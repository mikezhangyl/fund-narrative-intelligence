from __future__ import annotations

import json

from scripts import run_fund_holding_exposure_report
from src.scanners.fund_holding_exposure_report import (
    FundHoldingExposureConfig,
    execute_fund_holding_exposure_report,
    render_html_report,
)


class FakeFundExposureSource:
    degradation_events = [{"capability": "fund_holdings", "reason": "cache_hit"}]

    def fetch_fund_profile(self, *, fund_code):
        return [
            {
                "fund_code": fund_code,
                "fund_name": "招商中证白酒指数",
                "fund_type": "index_fund",
                "currency": "CNY",
                "source": "tushare",
            }
        ]

    def fetch_fund_holdings(self, *, fund_code, limit):
        rows = [
            {
                "fund_code": fund_code,
                "as_of_date": "2026-03-31",
                "stock_code": "600519",
                "ts_code": "600519.SH",
                "stock_name": "贵州茅台",
                "weight": 0.1833,
                "industry": "食品饮料",
                "source": "eastmoney",
            },
            {
                "fund_code": fund_code,
                "as_of_date": "2026-03-31",
                "stock_code": "000858",
                "ts_code": "000858.SZ",
                "stock_name": "五粮液",
                "weight": 0.1614,
                "industry": "食品饮料",
                "source": "eastmoney",
            },
        ]
        return rows[:limit]

    def fetch_stock_sector_memberships(
        self,
        *,
        symbols,
        trade_date,
        sector_types,
        limit_per_symbol,
        sector_universe_limit,
    ):
        del limit_per_symbol
        del sector_universe_limit
        rows = [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "trade_date": trade_date,
                "sector_name": "白酒概念",
                "sector_type": sector_types[0],
                "source": "eastmoney",
            },
            {
                "symbol": "000858.SZ",
                "name": "五粮液",
                "trade_date": trade_date,
                "sector_name": "白酒概念",
                "sector_type": sector_types[0],
                "source": "eastmoney",
            },
        ]
        requested = set(symbols)
        return [row for row in rows if row["symbol"] in requested]


class MembershipFailureSource(FakeFundExposureSource):
    def fetch_stock_sector_memberships(self, **kwargs):
        del kwargs
        raise RuntimeError("REQUEST_TIMEOUT: reverse index timed out")


NARRATIVE_REGISTRY = {
    "narratives": [
        {
            "narrative_id": "N_BAIJIU_CONSUMPTION",
            "display_name": "高端白酒消费",
            "name": "Premium Baijiu Consumption",
        }
    ]
}

STOCK_MAPPINGS = [
    {
        "stock_code": "600519",
        "narrative_id": "N_BAIJIU_CONSUMPTION",
        "mapping_weight": 0.9,
        "confidence": 0.86,
        "method": "test_mapping",
    },
    {
        "stock_code": "000858",
        "narrative_id": "N_BAIJIU_CONSUMPTION",
        "mapping_weight": 0.8,
        "confidence": 0.82,
        "method": "test_mapping",
    },
]


def test_execute_fund_holding_exposure_report_aggregates_gateway_holdings():
    report = execute_fund_holding_exposure_report(
        data_source=FakeFundExposureSource(),
        config=FundHoldingExposureConfig(
            fund_code="161725",
            sector_trade_date="2026-05-22",
            limit=10,
            sector_types=("concept",),
            sector_universe_limit=0,
        ),
        narrative_registry=NARRATIVE_REGISTRY,
        stock_narrative_mappings=STOCK_MAPPINGS,
    )

    assert report["status"] == "completed"
    assert report["summary"]["holding_count"] == 2
    assert report["summary"]["sector_membership_row_count"] == 2
    assert report["fund"]["fund_name"] == "招商中证白酒指数"
    assert report["industry_exposures"] == [
        {
            "industry": "食品饮料",
            "raw_weight": 0.3447,
            "normalized_weight": 1.0,
            "holding_count": 2,
            "symbols": ["000858", "600519"],
            "names": ["五粮液", "贵州茅台"],
        }
    ]
    assert report["sector_exposures"][0]["sector_name"] == "白酒概念"
    assert report["sector_exposures"][0]["raw_weight"] == 0.3447
    assert report["narrative_exposures"][0]["narrative_id"] == "N_BAIJIU_CONSUMPTION"
    assert report["narrative_exposures"][0]["narrative_name"] == "高端白酒消费"
    assert report["narrative_exposures"][0]["raw_exposure"] == 0.29409
    assert report["data_gaps"] == []


def test_execute_fund_holding_exposure_report_keeps_partial_result_on_membership_failure():
    report = execute_fund_holding_exposure_report(
        data_source=MembershipFailureSource(),
        config=FundHoldingExposureConfig(
            fund_code="161725",
            sector_trade_date="2026-05-22",
            limit=10,
        ),
        narrative_registry=NARRATIVE_REGISTRY,
        stock_narrative_mappings=[],
    )

    assert report["status"] == "partial"
    assert report["industry_exposures"][0]["industry"] == "食品饮料"
    assert report["sector_exposures"] == []
    assert report["narrative_exposures"] == []
    assert report["failures"][0]["capability"] == "stock_sector_membership"
    assert {
        "sector_membership_unavailable",
        "unmapped_fund_holding_symbols",
    }.issubset({gap["scope"] for gap in report["data_gaps"]})


def test_render_fund_holding_exposure_html_contains_key_sections():
    report = execute_fund_holding_exposure_report(
        data_source=FakeFundExposureSource(),
        config=FundHoldingExposureConfig(
            fund_code="161725",
            sector_trade_date="2026-05-22",
            limit=10,
        ),
        narrative_registry=NARRATIVE_REGISTRY,
        stock_narrative_mappings=STOCK_MAPPINGS,
    )

    html = render_html_report(report)

    assert "<h1>基金持仓暴露报告</h1>" in html
    assert "招商中证白酒指数" in html
    assert "高端白酒消费" in html
    assert "不构成投资建议" in html


def test_run_fund_holding_exposure_report_writes_json_and_html(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_fund_holding_exposure_report,
        "ConsolidatedMarketDataSource",
        lambda: FakeFundExposureSource(),
    )
    monkeypatch.setattr(
        run_fund_holding_exposure_report,
        "load_intelligence_context",
        lambda registry_mode, stock_mapping_mode: (NARRATIVE_REGISTRY, STOCK_MAPPINGS),
    )

    exit_code = run_fund_holding_exposure_report.main(
        [
            "--fund-code",
            "161725",
            "--sector-trade-date",
            "2026-05-22",
            "--limit",
            "10",
            "--sector-universe-limit",
            "0",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "fund_holding_exposure_report.json").read_text())
    html = (tmp_path / "fund_holding_exposure_report.html").read_text()

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["summary"]["holding_count"] == 2
    assert payload["narrative_exposures"][0]["narrative_name"] == "高端白酒消费"
    assert "<h1>基金持仓暴露报告</h1>" in html
