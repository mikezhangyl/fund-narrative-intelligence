from src import local_env
from src.providers.tushare_market import TushareMarketDataProvider


def test_tushare_market_provider_returns_unavailable_without_token(monkeypatch):
    monkeypatch.setattr(local_env, "get_config_value", lambda name: None)
    provider = TushareMarketDataProvider(token=None)

    payload = provider.get_stock_quotes(["600519"])

    assert payload["provider_name"] == "tushare-market-quote"
    assert payload["data_quality"] == "unavailable"
    assert payload["quotes"] == []
    assert payload["missing_stock_codes"] == ["600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"
    assert "TUSHARE_TOKEN" in provider.degradation_events[-1]["reason"]


def test_tushare_market_provider_maps_daily_rows():
    def fake_fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict:
        assert token == "test-token"
        assert params == {"ts_code": "600519.SH"}
        if api_name == "stock_basic":
            assert fields == "ts_code,symbol,name,industry"
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": ["ts_code", "symbol", "name", "industry"],
                    "items": [["600519.SH", "600519", "贵州茅台", "食品饮料"]],
                },
            }
        assert api_name == "daily"
        assert "pct_chg" in fields
        return {
            "code": 0,
            "msg": "",
            "data": {
                "fields": [
                    "ts_code",
                    "trade_date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "pre_close",
                    "change",
                    "pct_chg",
                    "vol",
                    "amount",
                ],
                "items": [
                    ["600519.SH", "20250514", 1550.0, 1568.0, 1544.0, 1560.0, 1530.0, 30.0, 1.96, 123456.0, 987654321.0]
                ],
            },
        }

    provider = TushareMarketDataProvider(token="test-token", fetcher=fake_fetcher)

    payload = provider.get_stock_quotes(["600519"])

    assert payload["provider_name"] == "tushare-market-quote"
    assert payload["data_quality"] == "fresh"
    assert payload["missing_stock_codes"] == []
    assert payload["quotes"][0]["stock_code"] == "600519"
    assert payload["quotes"][0]["stock_name"] == "贵州茅台"
    assert payload["quotes"][0]["latest_price"] == 1560.0
    assert payload["quotes"][0]["change_percent"] == 1.96
    assert payload["quotes"][0]["change_amount"] == 30.0
    assert payload["quotes"][0]["previous_close"] == 1530.0
    assert payload["quotes"][0]["volume"] == 123456.0
    assert payload["quotes"][0]["amount"] == 987654321.0


def test_tushare_market_provider_prefers_local_env_token(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "process-token")
    monkeypatch.setattr(local_env, "get_config_value", lambda name: "local-token")

    observed_tokens: list[str] = []

    def fake_fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict:
        observed_tokens.append(token)
        if api_name == "stock_basic":
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": ["ts_code", "symbol", "name", "industry"],
                    "items": [["600519.SH", "600519", "贵州茅台", "食品饮料"]],
                },
            }
        assert api_name == "daily"
        return {
            "code": 0,
            "msg": "",
            "data": {
                "fields": [
                    "ts_code",
                    "trade_date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "pre_close",
                    "change",
                    "pct_chg",
                    "vol",
                    "amount",
                ],
                "items": [["600519.SH", "20250514", 1.0, 2.0, 0.5, 1.5, 1.0, 0.5, 50.0, 100.0, 200.0]],
            },
        }

    provider = TushareMarketDataProvider(fetcher=fake_fetcher)
    provider.get_stock_quotes(["600519"])

    assert observed_tokens == ["local-token", "local-token"]
