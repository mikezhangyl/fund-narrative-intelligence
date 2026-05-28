from __future__ import annotations

import json

from scripts import run_structure_mapping_report
from src.scanners.structure_mapping_report import (
    StructureMappingReportConfig,
    execute_structure_mapping_report,
)


class FakeStructureMappingSource:
    degradation_events = [{"capability": "sector_constituents", "reason": "fallback"}]

    def fetch_sector_constituents(self, *, sector_name, trade_date, limit):
        return [
            {
                "sector_name": sector_name,
                "trade_date": trade_date,
                "symbol": "300024.SZ",
                "name": "机器人",
                "source": "eastmoney",
                "provider": "eastmoney",
            },
            {
                "sector_name": sector_name,
                "trade_date": trade_date,
                "symbol": "688017.SH",
                "name": "绿的谐波",
                "source": "eastmoney",
                "provider": "eastmoney",
            },
        ][:limit]

    def fetch_etf_basic(self, *, market, limit):
        return [
            {
                "symbol": "510300",
                "name": "沪深300ETF",
                "category": "宽基",
                "market": market,
                "source": "akshare",
                "provider": "akshare",
            },
            {
                "symbol": "159915",
                "name": "创业板ETF",
                "category": "宽基",
                "market": market,
                "source": "akshare",
                "provider": "akshare",
            },
        ][:limit]

    def fetch_index_constituents(self, *, index_symbol, trade_date, limit):
        return [
            {
                "index_symbol": index_symbol,
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "weight": 5.1,
                "source": "akshare",
                "provider": "akshare",
            }
        ][:limit]

    def fetch_margin_summary(self, *, trade_date):
        return {
            "trade_date": trade_date,
            "financing_balance": 2869272309416.0,
            "securities_lending_balance": 20930291159.0,
            "source": "akshare",
            "provider": "akshare",
        }

    def fetch_margin_detail(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "510050",
                "name": "50ETF",
                "financing_balance": 1538828149.0,
                "source": "akshare",
                "provider": "akshare",
            },
            {
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "financing_balance": 123000000.0,
                "source": "akshare",
                "provider": "akshare",
            },
        ][:limit]

    def fetch_earnings_calendar(self, *, start_date, end_date, limit):
        return [
            {
                "symbol": "920174",
                "name": "五新智能",
                "ann_date": start_date,
                "event_type": "公司章程修订",
                "source": "akshare",
                "provider": "akshare",
            },
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "ann_date": end_date,
                "event_type": "年度报告",
                "source": "akshare",
                "provider": "akshare",
            },
        ][:limit]


def test_execute_structure_mapping_report_combines_gateway_sections():
    report = execute_structure_mapping_report(
        data_source=FakeStructureMappingSource(),
        config=StructureMappingReportConfig(
            trade_date="2026-05-22",
            sector_name="机器人",
            index_symbol="000300.SH",
            event_start_date="2026-05-22",
            event_end_date="2026-06-05",
            limit=5,
        ),
    )

    assert report["status"] == "completed"
    assert report["components"]["sector_constituents"]["rows"][0]["name"] == "机器人"
    assert report["components"]["etf_basic"]["rows"][0]["category"] == "宽基"
    assert report["components"]["index_constituents"]["rows"][0]["weight"] == 5.1
    assert report["components"]["margin_summary"]["rows"][0]["financing_balance"] == 2869272309416.0
    assert report["components"]["margin_detail"]["rows"][0]["symbol"] == "510050"
    assert report["components"]["earnings_calendar"]["rows"][0]["event_type"] == "公司章程修订"
    assert report["data_footprint"]["total_rows"] == 10
    assert report["data_gap_summary"]["gap_count"] == 0
    assert report["summary"]["component_status_counts"]["completed"] == 6
    assert report["degradation_events"] == [
        {"capability": "sector_constituents", "reason": "fallback"}
    ]


def test_execute_structure_mapping_report_is_partial_when_components_fail():
    class FailingSource(FakeStructureMappingSource):
        def fetch_sector_constituents(self, **kwargs):
            raise RuntimeError("sector constituents unavailable")

        def fetch_etf_basic(self, **kwargs):
            return []

    report = execute_structure_mapping_report(
        data_source=FailingSource(),
        config=StructureMappingReportConfig(
            trade_date="2026-05-22",
            sector_name="机器人",
            index_symbol="000300.SH",
            event_start_date="2026-05-22",
            event_end_date="2026-06-05",
            limit=5,
        ),
    )

    assert report["status"] == "partial"
    assert report["components"]["sector_constituents"]["status"] == "failed"
    assert report["components"]["etf_basic"]["status"] == "missing"
    assert "sector constituents unavailable" in report["components"]["sector_constituents"]["failures"][0]["reason"]
    assert report["data_gap_summary"]["gap_count"] == 2


def test_run_structure_mapping_report_writes_json_and_html(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_structure_mapping_report,
        "ConsolidatedMarketDataSource",
        lambda: FakeStructureMappingSource(),
    )

    exit_code = run_structure_mapping_report.main(
        [
            "--trade-date",
            "2026-05-22",
            "--sector-name",
            "机器人",
            "--index-symbol",
            "000300.SH",
            "--event-start-date",
            "2026-05-22",
            "--event-end-date",
            "2026-06-05",
            "--limit",
            "5",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "structure_mapping_report.json").read_text())
    html = (tmp_path / "structure_mapping_report.html").read_text()

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["data_footprint"]["total_rows"] == 10
    assert "<h1>市场结构映射报告</h1>" in html
    assert "板块成分股" in html
    assert "融资融券摘要" in html
    assert "不构成投资建议" in html
