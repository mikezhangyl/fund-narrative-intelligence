from __future__ import annotations

import json

from scripts import (
    run_cyq_chips_probe,
    run_dragon_tiger_probe,
    run_earnings_calendar_probe,
    run_etf_basic_probe,
    run_etf_flow_probe,
    run_etf_spot_probe,
    run_fund_profile_holdings_probe,
    run_index_constituents_probe,
    run_limit_up_down_probe,
    run_main_capital_flow_probe,
    run_margin_detail_probe,
    run_margin_summary_probe,
    run_news_briefs_smoke,
    run_northbound_capital_probe,
    run_sector_constituents_probe,
    run_stock_sector_memberships_probe,
)


class FakeCanDoSource:
    degradation_events = [{"capability": "gateway_probe", "reason": "fake"}]

    def fetch_etf_spot(self, *, limit):
        return [
            {
                "symbol": "510300",
                "name": "沪深300ETF",
                "pct_change": 1.4,
                "source": "akshare",
            }
        ][:limit]

    def fetch_limit_up_down_stats(self, *, trade_date):
        return {
            "trade_date": trade_date,
            "limit_up_count": 2,
            "limit_down_count": 1,
            "source": "akshare",
        }

    def fetch_news_briefs(
        self,
        *,
        source_provider,
        src,
        start_datetime,
        end_datetime,
        limit,
    ):
        return [
            {
                "datetime": start_datetime,
                "title": f"{source_provider}:{src}",
                "content": end_datetime,
                "source": "tushare",
            }
        ][:limit]

    def fetch_northbound_capital(self, *, trade_date):
        return {
            "trade_date": trade_date,
            "net_buy_amount": 12.3,
            "source": "eastmoney",
        }

    def fetch_main_capital_flow(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "main_net_inflow": 123.0,
                "source": "eastmoney",
            }
        ][:limit]

    def fetch_etf_flow(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "510300.SH",
                "net_inflow": 456.0,
                "source": "eastmoney",
            }
        ][:limit]

    def fetch_dragon_tiger(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "000001.SZ",
                "reason": "日涨幅偏离值达7%",
                "source": "akshare",
            }
        ][:limit]

    def fetch_sector_constituents(self, *, sector_name, trade_date, limit):
        return [
            {
                "sector_name": sector_name,
                "trade_date": trade_date,
                "symbol": "300024.SZ",
                "name": "机器人",
                "source": "akshare",
            }
        ][:limit]

    def fetch_etf_basic(self, *, market, limit):
        return [
            {
                "symbol": "510300",
                "name": "沪深300ETF",
                "category": market,
                "source": "akshare",
            }
        ][:limit]

    def fetch_index_constituents(self, *, index_symbol, trade_date, limit):
        return [
            {
                "index_symbol": index_symbol,
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "source": "akshare",
            }
        ][:limit]

    def fetch_margin_summary(self, *, trade_date):
        return {
            "trade_date": trade_date,
            "financing_balance": 1800000000000.0,
            "source": "akshare",
        }

    def fetch_margin_detail(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "financing_balance": 123000000.0,
                "source": "akshare",
            }
        ][:limit]

    def fetch_earnings_calendar(self, *, start_date, end_date, limit):
        return [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "ann_date": start_date,
                "event_type": end_date,
                "source": "akshare",
            }
        ][:limit]

    def fetch_cyq_chips(self, *, symbols, trade_date):
        return [
            {
                "symbol": symbols[0],
                "trade_date": trade_date,
                "cost_distribution": [{"price": 1500.0, "percent": 0.32}],
                "source": "tushare",
            }
        ]

    def fetch_stock_sector_memberships(
        self,
        *,
        symbols,
        trade_date,
        sector_types,
        limit_per_symbol,
        sector_universe_limit,
    ):
        return [
            {
                "symbol": symbols[-1],
                "trade_date": trade_date,
                "sector_name": "机器人概念",
                "sector_type": sector_types[0],
                "sector_universe_limit": sector_universe_limit,
                "source": "eastmoney",
            }
        ][:limit_per_symbol]

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
        return [
            {
                "fund_code": fund_code,
                "as_of_date": "2026-03-31",
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "weight": 0.1833,
                "source": "eastmoney",
            }
        ][:limit]


def test_run_etf_spot_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_etf_spot_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_etf_spot_probe.main(
        ["--limit", "5", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "etf_spot_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["row_count"] == 1
    assert (tmp_path / "etf_spot_report.md").is_file()


def test_run_limit_up_down_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_limit_up_down_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_limit_up_down_probe.main(
        ["--trade-date", "2026-05-22", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "limit_up_down_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["row_count"] == 1
    assert (tmp_path / "limit_up_down_report.md").is_file()


def test_run_news_briefs_smoke_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_news_briefs_smoke,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_news_briefs_smoke.main(
        [
            "--src",
            "sina",
            "--start-datetime",
            "2026-05-22 09:00:00",
            "--end-datetime",
            "2026-05-22 15:30:00",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "news_briefs_smoke_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["row_count"] == 1
    assert (tmp_path / "news_briefs_smoke_report.md").is_file()


def test_run_northbound_capital_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_northbound_capital_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_northbound_capital_probe.main(
        ["--trade-date", "2026-05-22", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "northbound_capital_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["net_buy_amount"] == 12.3
    assert (tmp_path / "northbound_capital_report.md").is_file()


def test_run_main_capital_flow_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_main_capital_flow_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_main_capital_flow_probe.main(
        ["--trade-date", "2026-05-22", "--limit", "5", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "main_capital_flow_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["main_net_inflow"] == 123.0
    assert (tmp_path / "main_capital_flow_report.md").is_file()


def test_run_etf_flow_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_etf_flow_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_etf_flow_probe.main(
        ["--trade-date", "2026-05-22", "--limit", "5", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "etf_flow_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["net_inflow"] == 456.0
    assert (tmp_path / "etf_flow_report.md").is_file()


def test_run_dragon_tiger_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_dragon_tiger_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_dragon_tiger_probe.main(
        ["--trade-date", "2026-05-22", "--limit", "5", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "dragon_tiger_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["reason"] == "日涨幅偏离值达7%"
    assert (tmp_path / "dragon_tiger_report.md").is_file()


def test_run_sector_constituents_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_sector_constituents_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_sector_constituents_probe.main(
        [
            "--sector-name",
            "机器人",
            "--trade-date",
            "2026-05-22",
            "--limit",
            "5",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "sector_constituents_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["name"] == "机器人"
    assert (tmp_path / "sector_constituents_report.md").is_file()


def test_run_etf_basic_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_etf_basic_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_etf_basic_probe.main(
        ["--market", "cn", "--limit", "5", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "etf_basic_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["category"] == "cn"
    assert (tmp_path / "etf_basic_report.md").is_file()


def test_run_index_constituents_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_index_constituents_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_index_constituents_probe.main(
        [
            "--index-symbol",
            "000300.SH",
            "--trade-date",
            "2026-05-22",
            "--limit",
            "5",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "index_constituents_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["index_symbol"] == "000300.SH"
    assert (tmp_path / "index_constituents_report.md").is_file()


def test_run_margin_summary_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_margin_summary_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_margin_summary_probe.main(
        ["--trade-date", "2026-05-22", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "margin_summary_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["financing_balance"] == 1800000000000.0
    assert (tmp_path / "margin_summary_report.md").is_file()


def test_run_margin_detail_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_margin_detail_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_margin_detail_probe.main(
        ["--trade-date", "2026-05-22", "--limit", "5", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "margin_detail_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["symbol"] == "600519.SH"
    assert (tmp_path / "margin_detail_report.md").is_file()


def test_run_earnings_calendar_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_earnings_calendar_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_earnings_calendar_probe.main(
        [
            "--start-date",
            "2026-05-22",
            "--end-date",
            "2026-06-05",
            "--limit",
            "5",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "earnings_calendar_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["event_type"] == "2026-06-05"
    assert (tmp_path / "earnings_calendar_report.md").is_file()


def test_run_cyq_chips_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_cyq_chips_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_cyq_chips_probe.main(
        [
            "--symbols",
            "600519.SH",
            "--trade-date",
            "2026-05-22",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "cyq_chips_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["cost_distribution"][0]["percent"] == 0.32
    assert (tmp_path / "cyq_chips_report.md").is_file()


def test_run_stock_sector_memberships_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_stock_sector_memberships_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_stock_sector_memberships_probe.main(
        [
            "--symbols",
            "600519.SH,300024.SZ",
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

    payload = json.loads((tmp_path / "stock_sector_memberships_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["rows"][0]["sector_name"] == "机器人概念"
    assert payload["result"]["rows"][0]["sector_universe_limit"] == 0
    assert (tmp_path / "stock_sector_memberships_report.md").is_file()


def test_run_fund_profile_holdings_probe_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_fund_profile_holdings_probe,
        "ConsolidatedMarketDataSource",
        lambda: FakeCanDoSource(),
    )

    exit_code = run_fund_profile_holdings_probe.main(
        ["--fund-code", "161725", "--limit", "10", "--output-dir", str(tmp_path)]
    )

    payload = json.loads((tmp_path / "fund_profile_holdings_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["fund_code"] == "161725"
    assert payload["result"]["profile_row_count"] == 1
    assert payload["result"]["holding_row_count"] == 1
    assert payload["result"]["holdings"][0]["stock_code"] == "600519"
    assert (tmp_path / "fund_profile_holdings_report.md").is_file()
