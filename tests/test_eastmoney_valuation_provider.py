from urllib.error import URLError

from src.providers.eastmoney_valuation import (
    EASTMONEY_VALUATION_URL,
    EastmoneyValuationProvider,
    build_eastmoney_valuation_url,
    normalize_eastmoney_valuation_response,
)


def test_builds_eastmoney_valuation_url_with_quote_detail_fields():
    url = build_eastmoney_valuation_url("600519")

    assert url.startswith(EASTMONEY_VALUATION_URL)
    assert "secid=1.600519" in url
    assert "fields=" in url
    assert "f162" in url
    assert "f167" in url
    assert "f116" in url


def test_normalizes_eastmoney_valuation_response():
    payload = normalize_eastmoney_valuation_response(
        response={
            "rc": 0,
            "data": {
                "f43": 134217,
                "f57": "600519",
                "f58": "贵州茅台",
                "f60": 134409,
                "f116": 1680759514466.55,
                "f117": 1680759514466.55,
                "f162": 1542,
                "f167": 620,
                "f168": 44,
                "f170": -14,
            },
        },
        requested_stock_codes=["600519", "000858"],
        source_url="https://example.test/valuation",
        retrieved_at="2026-05-14T00:00:00+00:00",
    )

    assert payload == {
        "version": "valuation-snapshot-v1",
        "provider_name": "eastmoney-valuation",
        "provider_version": "eastmoney-valuation-v1",
        "data_quality": "partial",
        "source_url": "https://example.test/valuation",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "valuation_basis": "provider_valuation_metrics",
        "valuations": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "latest_price": 1342.17,
                "previous_close": 1344.09,
                "price_change_percent": -0.14,
                "valuation_pressure": "neutral",
                "source": "provider_valuation_metrics",
                "source_provider": "eastmoney-valuation",
                "source_url": "https://example.test/valuation",
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "pe_ttm": 15.42,
                "pb": 6.2,
                "market_cap": 1680759514466.55,
                "float_market_cap": 1680759514466.55,
                "turnover_rate": 0.44,
            }
        ],
        "missing_stock_codes": ["000858"],
    }


def test_eastmoney_valuation_provider_returns_unavailable_without_crashing():
    def failing_fetcher(_url: str) -> dict:
        raise URLError("network unavailable")

    provider = EastmoneyValuationProvider(fetcher=failing_fetcher)

    payload = provider.get_valuation_snapshots(["600519"])

    assert payload["provider_name"] == "eastmoney-valuation"
    assert payload["data_quality"] == "unavailable"
    assert payload["valuations"] == []
    assert payload["missing_stock_codes"] == ["600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"
