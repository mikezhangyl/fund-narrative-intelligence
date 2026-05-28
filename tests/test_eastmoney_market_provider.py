from urllib.error import URLError

from src.providers.eastmoney_market import (
    EASTMONEY_MARKET_QUOTE_URL,
    EastmoneyMarketDataProvider,
    build_eastmoney_quote_url,
    build_yahoo_quote_url,
    normalize_eastmoney_quote_response,
)


def test_builds_eastmoney_quote_url_with_market_prefixed_secids():
    url = build_eastmoney_quote_url("600519")

    assert url.startswith(EASTMONEY_MARKET_QUOTE_URL)
    assert "secid=1.600519" in url
    assert "klt=101" in url


def test_builds_yahoo_quote_url_for_hong_kong_stock():
    url = build_yahoo_quote_url("00700")

    assert "0700.HK" in url
    assert "interval=1d" in url


def test_normalizes_eastmoney_quote_response():
    payload = normalize_eastmoney_quote_response(
        response={
            "rc": 0,
            "data": {
                "code": "600519",
                "name": "贵州茅台",
                "klines": [
                    "2026-05-14,1338.00,1342.17,1369.06,1335.18,55244,7428592859.0,2.52,-0.14,-1.92,0.44"
                ],
            },
        },
        requested_stock_codes=["600519", "000858"],
        source_url="https://example.test/quotes",
        retrieved_at="2026-05-14T00:00:00+00:00",
    )

    assert payload == {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "eastmoney-market-quote",
        "provider_version": "eastmoney-market-quote-v1",
        "data_quality": "partial",
        "source_url": "https://example.test/quotes",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "quotes": [
                {
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                    "source_provider": "eastmoney",
                    "source_url": "https://example.test/quotes",
                    "latest_price": 1342.17,
                "change_percent": -0.14,
                "change_amount": -1.92,
                "volume": 55244,
                "amount": 7428592859.0,
                "high": 1369.06,
                "low": 1335.18,
                "open": 1338.0,
                "previous_close": 1344.09,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
            }
        ],
        "missing_stock_codes": ["000858"],
    }


def test_eastmoney_market_provider_returns_unavailable_without_crashing():
    def failing_fetcher(_url: str) -> dict:
        raise URLError("network unavailable")

    provider = EastmoneyMarketDataProvider(
        fetcher=failing_fetcher,
        yahoo_fetcher=failing_fetcher,
    )

    payload = provider.get_stock_quotes(["600519"])

    assert payload["data_quality"] == "unavailable"
    assert payload["quotes"] == []
    assert payload["missing_stock_codes"] == ["600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"


def test_eastmoney_market_provider_falls_back_to_yahoo_chart():
    def failing_eastmoney(_url: str) -> dict:
        raise URLError("eastmoney unavailable")

    def fake_yahoo(_url: str) -> dict:
        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "symbol": "600519.SS",
                            "shortName": "贵州茅台",
                            "chartPreviousClose": 1344.09,
                        },
                        "timestamp": [1778722200],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [1338.0],
                                    "close": [1342.17],
                                    "high": [1369.06],
                                    "low": [1335.18],
                                    "volume": [55244],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }

    provider = EastmoneyMarketDataProvider(
        fetcher=failing_eastmoney,
        yahoo_fetcher=fake_yahoo,
    )

    payload = provider.get_stock_quotes(["600519"])

    assert payload["provider_name"] == "yahoo-chart"
    assert payload["data_quality"] == "fresh"
    assert payload["quotes"][0]["source_provider"] == "yahoo-chart"
    assert payload["quotes"][0]["change_amount"] == -1.92
    assert provider.degradation_events[0]["type"] == "provider_fallback"


def test_eastmoney_market_provider_uses_yahoo_directly_for_hong_kong_stock():
    called = {"eastmoney": 0, "yahoo": 0}

    def fake_eastmoney(_url: str) -> dict:
        called["eastmoney"] += 1
        raise AssertionError("Hong Kong stocks should not call A-share Eastmoney quote path")

    def fake_yahoo(url: str) -> dict:
        called["yahoo"] += 1
        assert "0700.HK" in url
        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "symbol": "0700.HK",
                            "shortName": "腾讯控股",
                            "chartPreviousClose": 560.0,
                        },
                        "timestamp": [1778722200],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [563.0],
                                    "close": [551.0],
                                    "high": [566.0],
                                    "low": [547.0],
                                    "volume": [29212000],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }

    provider = EastmoneyMarketDataProvider(
        fetcher=fake_eastmoney,
        yahoo_fetcher=fake_yahoo,
    )

    payload = provider.get_stock_quotes(["00700"])

    assert payload["provider_name"] == "yahoo-chart"
    assert payload["data_quality"] == "fresh"
    assert payload["quotes"][0]["stock_code"] == "00700"
    assert payload["quotes"][0]["stock_name"] == "腾讯控股"
    assert called == {"eastmoney": 0, "yahoo": 1}
