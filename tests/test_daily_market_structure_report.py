from __future__ import annotations

import json

from scripts import run_daily_market_structure_report
from src.scanners.daily_market_structure_report import (
    DailyMarketStructureReportConfig,
    execute_daily_market_structure_report,
)


class FakeMarketStructureSource:
    degradation_events = [{"capability": "example", "reason": "fallback"}]

    def fetch_trade_calendar(self, **kwargs):
        return [
            {"exchange": kwargs["exchange"], "cal_date": "2026-05-21", "is_open": 1},
            {"exchange": kwargs["exchange"], "cal_date": "2026-05-22", "is_open": 1},
        ]

    def fetch_breadth_window_bars(self, **kwargs):
        return [
            {
                "symbol": "AAA",
                "trade_date": "2026-05-21",
                "close": 1.0,
                "pre_close": 0.9,
                "volume": 10.0,
            },
            {
                "symbol": "AAA",
                "trade_date": "2026-05-22",
                "close": 1.2,
                "pre_close": 1.0,
                "volume": 12.0,
            },
            {
                "symbol": "BBB",
                "trade_date": "2026-05-21",
                "close": 2.0,
                "pre_close": 2.1,
                "volume": 20.0,
            },
            {
                "symbol": "BBB",
                "trade_date": "2026-05-22",
                "close": 1.8,
                "pre_close": 2.0,
                "volume": 18.0,
            },
        ]

    def fetch_index_bars(self, *, symbols, start_date, end_date):
        return [
            {
                "symbol": symbol,
                "trade_date": end_date,
                "close": 3500.0 + index,
                "pre_close": 3490.0 + index,
                "source": "tushare",
                "provider": "local_gateway",
            }
            for index, symbol in enumerate(symbols)
        ]

    def fetch_etf_data(self, *, symbols, start_date, end_date):
        return [
            {
                "symbol": symbol,
                "trade_date": end_date,
                "close": 4.2 + index,
                "pre_close": 4.1 + index,
                "source": "tushare",
                "provider": "local_gateway",
            }
            for index, symbol in enumerate(symbols)
        ]

    def fetch_sector_data(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "sector_name": "机器人",
                "pct_change": 3.2,
                "amount": 100.0,
                "source": "gateway",
                "provider": "akshare",
            },
            {
                "trade_date": trade_date,
                "sector_name": "银行",
                "pct_change": -0.5,
                "amount": 80.0,
                "source": "gateway",
                "provider": "akshare",
            },
        ][:limit]

    def fetch_etf_spot(self, *, limit):
        return [
            {
                "symbol": "159915",
                "name": "创业板ETF",
                "pct_change": 2.1,
                "amount": 50.0,
                "source": "gateway",
                "provider": "akshare",
            }
        ][:limit]

    def fetch_limit_up_down_stats(self, *, trade_date):
        return {
            "trade_date": trade_date,
            "limit_up_count": 45,
            "limit_down_count": 3,
            "source": "gateway",
            "provider": "akshare",
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
                "title": "政策支持机器人产业链",
                "content": "机器人产业链资金活跃。",
                "channels": "产业",
                "source": "tushare",
                "provider": source_provider,
                "src": src,
            },
            {
                "datetime": start_datetime,
                "title": "政策支持机器人产业链",
                "content": "机器人产业链资金活跃。",
                "channels": "公司",
                "source": "tushare",
                "provider": source_provider,
                "src": src,
            },
            {
                "datetime": end_datetime,
                "title": "ETF 成交额回升",
                "content": "宽基 ETF 热度提升。",
                "channels": "市场",
                "source": "tushare",
                "provider": source_provider,
                "src": src,
            },
        ][:limit]

    def fetch_sector_constituents(self, *, sector_name, trade_date, limit):
        return [
            {
                "sector_name": sector_name,
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "pct_change": 1.2,
                "source": "eastmoney",
                "provider": "eastmoney",
            },
            {
                "sector_name": sector_name,
                "trade_date": trade_date,
                "symbol": "300024.SZ",
                "name": "机器人",
                "pct_change": 3.1,
                "source": "eastmoney",
                "provider": "eastmoney",
            }
        ][:limit]

    def fetch_etf_basic(self, *, market, limit):
        return [
            {
                "symbol": "510300",
                "name": "沪深300ETF",
                "category": market,
                "source": "akshare",
                "provider": "akshare",
            }
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
            "source": "akshare",
            "provider": "akshare",
        }

    def fetch_margin_detail(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "financing_balance": 2538828149.0,
                "source": "akshare",
                "provider": "akshare",
            },
            {
                "trade_date": trade_date,
                "symbol": "510050",
                "name": "50ETF",
                "financing_balance": 1538828149.0,
                "source": "akshare",
                "provider": "akshare",
            }
        ][:limit]

    def fetch_earnings_calendar(self, *, start_date, end_date, limit):
        return [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "ann_date": start_date,
                "event_type": "年度报告",
                "source": "akshare",
                "provider": "akshare",
            },
            {
                "symbol": "920174",
                "name": "五新智能",
                "ann_date": start_date,
                "event_type": end_date,
                "source": "akshare",
                "provider": "akshare",
            }
        ][:limit]

    def fetch_northbound_capital(self, *, trade_date):
        return {
            "trade_date": trade_date,
            "net_buy_amount": 11.2,
            "buy_amount": 51.2,
            "sell_amount": 40.0,
            "source": "eastmoney",
            "provider": "eastmoney",
        }

    def fetch_main_capital_flow(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "300024.SZ",
                "name": "机器人",
                "main_net_inflow": 123.0,
                "pct_change": 3.1,
                "source": "eastmoney",
                "provider": "eastmoney",
            },
            {
                "trade_date": trade_date,
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "main_net_inflow": 98.0,
                "pct_change": 1.2,
                "source": "eastmoney",
                "provider": "eastmoney",
            },
        ][:limit]

    def fetch_etf_flow(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "159915",
                "name": "创业板ETF",
                "net_inflow": 45.0,
                "pct_change": 2.1,
                "source": "eastmoney",
                "provider": "eastmoney",
            }
        ][:limit]

    def fetch_dragon_tiger(self, *, trade_date, limit):
        return [
            {
                "trade_date": trade_date,
                "symbol": "300024.SZ",
                "name": "机器人",
                "reason": "日涨幅偏离值达7%",
                "net_buy_amount": 15.0,
                "source": "akshare",
                "provider": "akshare",
            }
        ][:limit]

    def fetch_cyq_chips(self, *, symbols, trade_date):
        return [
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "cost_distribution": [
                    {"price": 10.0, "percent": 0.30},
                    {"price": 12.0, "percent": 0.22},
                ],
                "source": "tushare",
                "provider": "local_gateway",
            }
            for symbol in symbols
        ]


def test_execute_daily_market_structure_report_combines_can_do_sections():
    report = execute_daily_market_structure_report(
        data_source=FakeMarketStructureSource(),
        config=DailyMarketStructureReportConfig(
            trade_date="2026-05-22",
            breadth_symbols=("AAA", "BBB"),
            breadth_lookback_trading_days=2,
            sector_limit=2,
            etf_limit=1,
            news_limit=3,
            news_start_datetime="2026-05-22 09:00:00",
            news_end_datetime="2026-05-22 15:30:00",
        ),
    )

    assert report["status"] == "completed"
    assert report["components"]["market_breadth"]["status"] == "completed"
    assert report["components"]["market_breadth"]["data_fetch_mode"] == "breadth_window"
    assert report["components"]["market_breadth"]["row_count"] == 4
    assert report["components"]["sector_heat"]["top_rows"][0]["sector_name"] == "机器人"
    assert report["components"]["etf_heat"]["top_rows"][0]["symbol"] == "159915"
    assert report["components"]["limit_temperature"]["temperature_label"] == "hot"
    assert report["components"]["news_summary"]["raw_headline_count"] == 3
    assert report["components"]["news_summary"]["headline_count"] == 2
    assert report["components"]["news_summary"]["duplicate_count"] == 1
    assert report["components"]["news_summary"]["briefs"][0]["duplicate_count"] == 2
    assert report["components"]["structure_mapping"]["status"] == "completed"
    assert report["components"]["structure_mapping"]["row_count"] == 9
    assert report["components"]["structure_mapping"]["components"]["sector_constituents"]["rows"][0]["name"] == "贵州茅台"
    assert report["components"]["flow_event_context"]["status"] == "completed"
    assert report["components"]["flow_event_context"]["row_count"] == 5
    assert report["components"]["flow_event_context"]["northbound_label"] == "net_buy"
    assert report["components"]["flow_event_context"]["top_main_flow"][0]["name"] == "机器人"
    assert "机器人 / 300024.SZ" in report["components"]["flow_event_context"]["cross_links"][0]["samples"]
    assert report["components"]["cost_basis_context"]["status"] == "completed"
    assert report["components"]["cost_basis_context"]["row_count"] == 2
    assert report["components"]["cost_basis_context"]["chip_summaries"][0]["distribution_bucket_count"] == 2
    assert report["components"]["cost_basis_context"]["chip_summaries"][0]["peak_percent"] == 0.3
    assert report["components"]["benchmark_context"]["status"] == "completed"
    assert report["components"]["benchmark_context"]["row_count"] == 3
    assert report["components"]["benchmark_context"]["index_rows"][0]["symbol"] == "000300.SH"
    assert report["components"]["benchmark_context"]["etf_rows"][0]["symbol"] == "510300.SH"
    assert report["data_footprint"]["news_rows"] == 3
    assert report["data_footprint"]["news_unique_rows"] == 2
    assert report["data_footprint"]["structure_mapping_rows"] == 9
    assert report["data_footprint"]["flow_event_rows"] == 5
    assert report["data_footprint"]["cost_basis_rows"] == 2
    assert report["data_footprint"]["benchmark_rows"] == 3
    assert report["data_footprint"]["total_rows"] == 30
    assert report["data_gap_summary"]["gap_count"] == 0
    assert report["summary"]["component_status_counts"]["completed"] == 9
    assert report["degradation_events"] == [{"capability": "example", "reason": "fallback"}]


def test_execute_daily_market_structure_report_is_partial_when_components_fail():
    class FailingSource(FakeMarketStructureSource):
        def fetch_sector_data(self, *, trade_date, limit):
            raise RuntimeError("sector unavailable")

        def fetch_news_briefs(self, **kwargs):
            raise RuntimeError("PROVIDER_PERMISSION_REQUIRED: no news permission")

    report = execute_daily_market_structure_report(
        data_source=FailingSource(),
        config=DailyMarketStructureReportConfig(
            trade_date="2026-05-22",
            breadth_symbols=("AAA", "BBB"),
            breadth_lookback_trading_days=2,
            news_start_datetime="2026-05-22 09:00:00",
            news_end_datetime="2026-05-22 15:30:00",
        ),
    )

    assert report["status"] == "partial"
    assert report["components"]["sector_heat"]["status"] == "failed"
    assert report["components"]["news_summary"]["status"] == "permission_required"
    assert "sector unavailable" in report["components"]["sector_heat"]["failures"][0]["reason"]


def test_run_daily_market_structure_report_writes_json_and_html(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_daily_market_structure_report,
        "ConsolidatedMarketDataSource",
        lambda: FakeMarketStructureSource(),
    )

    exit_code = run_daily_market_structure_report.main(
        [
            "--trade-date",
            "2026-05-22",
            "--breadth-symbols",
            "AAA,BBB",
            "--breadth-lookback-trading-days",
            "2",
            "--news-start-datetime",
            "2026-05-22 09:00:00",
            "--news-end-datetime",
            "2026-05-22 15:30:00",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "daily_market_structure_report.json").read_text())

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["components"]["news_summary"]["raw_headline_count"] == 3
    assert payload["components"]["news_summary"]["headline_count"] == 2
    assert payload["components"]["structure_mapping"]["status"] == "completed"
    assert payload["components"]["flow_event_context"]["status"] == "completed"
    assert payload["components"]["cost_basis_context"]["status"] == "completed"
    assert payload["components"]["benchmark_context"]["status"] == "completed"
    html = (tmp_path / "daily_market_structure_report.html").read_text()
    assert "<h1>每日市场结构报告</h1>" in html
    assert "涨跌幅（%）" in html
    assert "去重后新闻" in html
    assert "资金/事件上下文" in html
    assert "北向资金" in html
    assert "主题与主力资金交集" in html
    assert "主题与龙虎榜交集" in html
    assert "成本/筹码上下文" in html
    assert "筹码分布样本" in html
    assert "分布桶数" in html
    assert "指数/ETF 基准上下文" in html
    assert "指数日线样本" in html
    assert "ETF 日线样本" in html
    assert "市场结构映射（新增）" in html
    assert 'class="new-update"' in html
    assert "color: #b91c1c" in html
    assert "结构解释线索" in html
    assert "交叉线索" in html
    assert "主题与指数交集" in html
    assert "主题与融资融券交集" in html
    assert "主题与事件日历交集" in html
    assert "可解释用途" in html
    assert "机器人 / 300024.SZ" in html
    assert "融资余额最高样本" in html
    assert "贵州茅台 / 600519.SH" in html
    assert "五新智能 / 920174" in html
    assert "<strong>0.0%</strong>" in html


def test_daily_market_structure_report_records_data_gaps():
    class GapSource(FakeMarketStructureSource):
        def fetch_breadth_window_bars(self, **kwargs):
            return [
                {
                    "symbol": "AAA",
                    "trade_date": "2026-05-22",
                    "close": 1.2,
                    "pre_close": 1.0,
                    "volume": 12.0,
                }
            ]

        def fetch_etf_spot(self, *, limit):
            return []

    report = execute_daily_market_structure_report(
        data_source=GapSource(),
        config=DailyMarketStructureReportConfig(
            trade_date="2026-05-22",
            breadth_symbols=("AAA", "BBB"),
            breadth_lookback_trading_days=2,
            sector_limit=2,
            etf_limit=3,
            news_limit=3,
            news_start_datetime="2026-05-22 09:00:00",
            news_end_datetime="2026-05-22 15:30:00",
        ),
    )

    scopes = {gap["scope"] for gap in report["data_gaps"]}

    assert report["status"] == "partial"
    assert "market_breadth_symbols" in scopes
    assert "market_breadth_bar_rows" in scopes
    assert "etf_heat_rows" in scopes
    assert report["data_gap_summary"]["gap_count"] == 3
