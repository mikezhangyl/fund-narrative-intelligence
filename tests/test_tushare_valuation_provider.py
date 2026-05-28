from src import local_env
from src.providers.tushare_valuation import TushareValuationProvider


def test_tushare_valuation_provider_returns_unavailable_without_token(monkeypatch):
    monkeypatch.setattr(local_env, "get_config_value", lambda name: None)
    provider = TushareValuationProvider(token=None)

    payload = provider.get_valuation_snapshots(["600519"])

    assert payload["provider_name"] == "tushare-valuation"
    assert payload["data_quality"] == "unavailable"
    assert payload["valuations"] == []
    assert payload["missing_stock_codes"] == ["600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"
    assert "TUSHARE_TOKEN" in provider.degradation_events[-1]["reason"]


def test_tushare_valuation_provider_maps_daily_rows():
    def fake_fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict:
        assert token == "test-token"
        assert params == {"ts_code": "600519.SH"}
        if api_name == "daily_basic":
            assert "pe_ttm" in fields
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": [
                        "ts_code",
                        "trade_date",
                        "close",
                        "turnover_rate",
                        "pe_ttm",
                        "pb",
                        "total_mv",
                        "circ_mv",
                    ],
                    "items": [
                        ["600519.SH", "20250515", 1560.0, 0.42, 24.6, 8.3, 1970000000.0, 1965000000.0]
                    ],
                },
            }
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
                "fields": ["ts_code", "trade_date", "pre_close", "pct_chg"],
                "items": [["600519.SH", "20250515", 1530.0, 1.96]],
            },
        }

    provider = TushareValuationProvider(token="test-token", fetcher=fake_fetcher)

    payload = provider.get_valuation_snapshots(["600519"])

    assert payload["provider_name"] == "tushare-valuation"
    assert payload["data_quality"] == "fresh"
    assert payload["missing_stock_codes"] == []
    assert payload["valuations"][0]["stock_code"] == "600519"
    assert payload["valuations"][0]["stock_name"] == "贵州茅台"
    assert payload["valuations"][0]["latest_price"] == 1560.0
    assert payload["valuations"][0]["previous_close"] == 1530.0
    assert payload["valuations"][0]["price_change_percent"] == 1.96
    assert payload["valuations"][0]["pe_ttm"] == 24.6
    assert payload["valuations"][0]["pb"] == 8.3
    assert payload["valuations"][0]["market_cap"] == 1970000000.0
    assert payload["valuations"][0]["float_market_cap"] == 1965000000.0
    assert payload["valuations"][0]["turnover_rate"] == 0.42
    assert payload["valuations"][0]["valuation_pressure"] == "elevated"


def test_tushare_valuation_provider_prefers_local_env_token(monkeypatch):
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
        if api_name == "daily_basic":
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": [
                        "ts_code",
                        "trade_date",
                        "close",
                        "turnover_rate",
                        "pe_ttm",
                        "pb",
                        "total_mv",
                        "circ_mv",
                    ],
                    "items": [
                        ["600519.SH", "20250515", 1560.0, 0.42, 24.6, 8.3, 1.0, 2.0]
                    ],
                },
            }
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
                "fields": ["ts_code", "trade_date", "pre_close", "pct_chg"],
                "items": [["600519.SH", "20250515", 1530.0, 1.96]],
            },
        }

    provider = TushareValuationProvider(fetcher=fake_fetcher)
    provider.get_valuation_snapshots(["600519"])

    assert observed_tokens == ["local-token", "local-token", "local-token"]
