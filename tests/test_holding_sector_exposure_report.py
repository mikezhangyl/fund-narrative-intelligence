from __future__ import annotations

import json

from scripts import run_holding_sector_exposure_report
from src.scanners.holding_sector_exposure_report import (
    HoldingSectorExposureConfig,
    execute_holding_sector_exposure_report,
)


class FakeHoldingSectorExposureSource:
    degradation_events = [{"capability": "stock_sector_membership", "reason": "cache"}]

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
                "symbol": "300024.SZ",
                "name": "机器人",
                "trade_date": trade_date,
                "sector_name": "机器人概念",
                "sector_type": sector_types[0],
                "source": "eastmoney",
            },
            {
                "symbol": "300024.SZ",
                "name": "机器人",
                "trade_date": trade_date,
                "sector_name": "人工智能",
                "sector_type": sector_types[0],
                "source": "eastmoney",
            },
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "trade_date": trade_date,
                "sector_name": "白酒",
                "sector_type": sector_types[0],
                "source": "eastmoney",
            },
        ]
        requested = set(symbols)
        return [row for row in rows if row["symbol"] in requested]


def test_execute_holding_sector_exposure_report_summarizes_memberships():
    report = execute_holding_sector_exposure_report(
        data_source=FakeHoldingSectorExposureSource(),
        config=HoldingSectorExposureConfig(
            symbols=("300024.SZ", "600519.SH", "000001.SZ"),
            trade_date="2026-05-22",
            sector_types=("concept",),
            limit_per_symbol=20,
            sector_universe_limit=0,
        ),
    )

    assert report["status"] == "partial"
    assert report["summary"]["requested_symbol_count"] == 3
    assert report["summary"]["covered_symbol_count"] == 2
    assert report["summary"]["missing_symbols"] == ["000001.SZ"]
    assert report["config"]["sector_universe_limit"] == 0
    assert report["sector_exposures"][0]["sector_name"] == "人工智能"
    assert report["sector_exposures"][0]["holding_count"] == 1
    assert report["data_gap_summary"]["gap_count"] == 1


def test_run_holding_sector_exposure_report_writes_json_and_html(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_holding_sector_exposure_report,
        "ConsolidatedMarketDataSource",
        lambda: FakeHoldingSectorExposureSource(),
    )

    exit_code = run_holding_sector_exposure_report.main(
        [
            "--symbols",
            "300024.SZ,600519.SH",
            "--trade-date",
            "2026-05-22",
            "--sector-types",
            "concept",
            "--limit-per-symbol",
            "20",
            "--sector-universe-limit",
            "0",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "holding_sector_exposure_report.json").read_text())
    html = (tmp_path / "holding_sector_exposure_report.html").read_text()

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["config"]["sector_universe_limit"] == 0
    assert payload["summary"]["covered_symbol_count"] == 2
    assert "<h1>持仓板块暴露报告</h1>" in html
    assert "机器人概念" in html
    assert "不构成投资建议" in html
