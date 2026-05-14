from urllib.error import URLError

from src.providers.eastmoney_market import (
    EASTMONEY_MARKET_QUOTE_URL,
    EastmoneyMarketDataProvider,
    build_eastmoney_quote_url,
    normalize_eastmoney_quote_response,
)


def test_builds_eastmoney_quote_url_with_market_prefixed_secids():
    url = build_eastmoney_quote_url("600519")

    assert url.startswith(EASTMONEY_MARKET_QUOTE_URL)
    assert "secid=1.600519" in url
    assert "klt=101" in url


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
