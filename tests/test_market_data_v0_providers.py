from __future__ import annotations

from src.market_data.cache import NullMarketDataCache
from src.market_data.providers.akshare import AkShareMarketDataProvider
from src.market_data.providers.tushare import TushareMarketDataProvider
from src.market_data.request_logging import InMemoryProviderRequestLogger
from src.providers.tushare_market import (
    TushareMarketDataProvider as ExistingTushareMarketQuoteProvider,
)


class _Frame:
    def __init__(self, rows: list[dict[str, object]]):
        self._rows = rows

    def to_dict(self, orient: str) -> list[dict[str, object]]:
        assert orient == "records"
        return self._rows


def test_tushare_v0_fetches_daily_bars_with_turnover_and_cache():
    calls: list[str] = []

    def fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict[str, object]:
        assert token == "token"
        calls.append(api_name)
        if api_name == "daily":
            return {
                "code": 0,
                "data": {
                    "fields": fields.split(","),
                    "items": [
                        [
                            "600519.SH",
                            "20260522",
                            1550.0,
                            1568.0,
                            1544.0,
                            1560.0,
                            1530.0,
                            123456.0,
                            987654321.0,
                        ]
                    ],
                },
            }
        if api_name == "daily_basic":
            return {
                "code": 0,
                "data": {
                    "fields": fields.split(","),
                    "items": [["600519.SH", "20260522", 0.42, 1.2, 21000.0, 18000.0]],
                },
            }
        raise AssertionError(api_name)

    logger = InMemoryProviderRequestLogger()
    provider = TushareMarketDataProvider(
        token="token",
        fetcher=fetcher,
        cache=NullMarketDataCache(),
        logger=logger,
        pacing_seconds=0,
    )

    rows = provider.fetch_daily_bars(
        symbols=["600519.SH"],
        start_date="20260522",
        end_date="20260522",
        include_turnover=True,
    )

    assert calls == ["daily", "daily_basic"]
    assert rows == [
        {
            "symbol": "600519.SH",
            "trade_date": "2026-05-22",
            "open": 1550.0,
            "high": 1568.0,
            "low": 1544.0,
            "close": 1560.0,
            "pre_close": 1530.0,
            "volume": 123456.0,
            "amount": 987654321.0,
            "turnover_rate": 0.42,
            "source": "tushare",
        }
    ]
    assert [entry.endpoint for entry in logger.entries] == ["daily", "daily_basic"]
    assert all(entry.status == "success" for entry in logger.entries)


def test_tushare_v0_retries_transient_failure():
    attempts = 0

    def fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("slow")
        return {
            "code": 0,
            "data": {
                "fields": fields.split(","),
                "items": [["000001.SH", "20260522", 3000.0, 3010.0, 2990.0, 3005.0, 3001.0, 1.0, 2.0]],
            },
        }

    logger = InMemoryProviderRequestLogger()
    provider = TushareMarketDataProvider(
        token="token",
        fetcher=fetcher,
        cache=NullMarketDataCache(),
        logger=logger,
        pacing_seconds=0,
        retry_attempts=2,
        retry_backoff_seconds=0,
    )

    rows = provider.fetch_index_bars(
        symbols=["000001.SH"],
        start_date="20260522",
        end_date="20260522",
    )

    assert rows[0]["symbol"] == "000001.SH"
    assert attempts == 2
    assert logger.entries[-1].retry_count == 1


def test_tushare_v0_fetches_trade_calendar():
    def fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict[str, object]:
        assert token == "token"
        assert api_name == "trade_cal"
        assert params == {
            "exchange": "SSE",
            "start_date": "20260522",
            "end_date": "20260525",
        }
        return {
            "code": 0,
            "data": {
                "fields": fields.split(","),
                "items": [
                    ["SSE", "20260522", 1, "20260521"],
                    ["SSE", "20260523", 0, "20260522"],
                ],
            },
        }

    logger = InMemoryProviderRequestLogger()
    provider = TushareMarketDataProvider(
        token="token",
        fetcher=fetcher,
        cache=NullMarketDataCache(),
        logger=logger,
        pacing_seconds=0,
    )

    rows = provider.fetch_trade_calendar(
        exchange="SSE",
        start_date="20260522",
        end_date="20260525",
    )

    assert rows == [
        {
            "exchange": "SSE",
            "cal_date": "2026-05-22",
            "is_open": True,
            "pretrade_date": "2026-05-21",
            "source": "tushare",
        },
        {
            "exchange": "SSE",
            "cal_date": "2026-05-23",
            "is_open": False,
            "pretrade_date": "2026-05-22",
            "source": "tushare",
        },
    ]
    assert logger.entries[-1].endpoint == "trade_cal"


def test_tushare_v0_reuses_existing_quote_provider_and_local_env(monkeypatch):
    monkeypatch.setattr(
        "src.local_env.get_config_value",
        lambda name: "local-token" if name == "TUSHARE_TOKEN" else None,
    )

    provider = TushareMarketDataProvider(fetcher=lambda *args: {})

    assert isinstance(provider.quote_provider, ExistingTushareMarketQuoteProvider)
    assert provider.token == "local-token"


def test_akshare_v0_fetches_sector_etf_and_limit_stats():
    class Client:
        def stock_board_concept_name_em(self):
            return _Frame(
                [
                    {
                        "代码": "BK1234",
                        "板块名称": "机器人概念",
                        "涨跌幅": 2.5,
                        "换手率": 3.1,
                        "成交额": 123000000.0,
                    }
                ]
            )

        def fund_etf_hist_em(
            self,
            symbol: str,
            period: str,
            start_date: str,
            end_date: str,
            adjust: str,
        ):
            assert (symbol, period, start_date, end_date, adjust) == (
                "510300",
                "daily",
                "20260522",
                "20260522",
                "",
            )
            return _Frame(
                [
                    {
                        "日期": "2026-05-22",
                        "开盘": 4.0,
                        "最高": 4.1,
                        "最低": 3.9,
                        "收盘": 4.05,
                        "成交量": 1000,
                        "成交额": 4050,
                    }
                ]
            )

        def stock_zt_pool_em(self, date: str):
            assert date == "20260522"
            return _Frame([{"代码": "600001"}, {"代码": "600002"}])

        def stock_zt_pool_dtgc_em(self, date: str):
            assert date == "20260522"
            return _Frame([{"代码": "000001"}])

    logger = InMemoryProviderRequestLogger()
    provider = AkShareMarketDataProvider(
        client=Client(),
        cache=NullMarketDataCache(),
        logger=logger,
        pacing_seconds=0,
    )

    sectors = provider.fetch_sector_data(trade_date="20260522")
    etfs = provider.fetch_etf_data(
        symbols=["510300"],
        start_date="20260522",
        end_date="20260522",
    )
    limit_stats = provider.fetch_limit_up_down_stats(trade_date="20260522")

    assert sectors[0]["sector_name"] == "机器人概念"
    assert etfs[0]["symbol"] == "510300"
    assert limit_stats == {
        "trade_date": "2026-05-22",
        "limit_up_count": 2,
        "limit_down_count": 1,
        "source": "akshare",
    }
    assert [entry.endpoint for entry in logger.entries] == [
        "stock_board_concept_name_em",
        "fund_etf_hist_em",
        "stock_zt_pool_em",
        "stock_zt_pool_dtgc_em",
    ]


def test_akshare_v0_reuses_existing_quote_provider_for_latest_quotes():
    class QuoteProvider:
        provider_name = "akshare-market-quote"
        client = None

        def get_stock_quotes(self, stock_codes):
            return {"provider_name": self.provider_name, "requested": stock_codes}

        def _load_client(self):
            raise AssertionError("not needed for latest quote delegation")

    provider = AkShareMarketDataProvider(quote_provider=QuoteProvider())

    assert provider.fetch_latest_stock_quotes(["600519"]) == {
        "provider_name": "akshare-market-quote",
        "requested": ["600519"],
    }
