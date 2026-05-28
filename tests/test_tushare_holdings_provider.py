from src import local_env
from src.providers.factory import select_data_provider
from src.providers.tushare_holdings import TushareFundHoldingProvider


def test_selects_tushare_provider_mode():
    selection = select_data_provider("tushare")

    assert isinstance(selection.provider, TushareFundHoldingProvider)


def test_tushare_holdings_provider_falls_back_to_mock_without_token(monkeypatch):
    monkeypatch.setattr(local_env, "get_config_value", lambda name: None)
    provider = TushareFundHoldingProvider(token=None)

    payload = provider.get_fund_holdings("000001")

    assert payload["fund"]["provider_metadata"]["data_quality"] == "mock"
    assert provider.degradation_events[-1]["type"] == "provider_fallback"
    assert provider.degradation_events[-1]["requested_provider_mode"] == "tushare"
    assert "TUSHARE_TOKEN" in provider.degradation_events[-1]["reason"]


def test_tushare_holdings_provider_maps_latest_fund_portfolio_rows():
    observed_ts_codes: list[str] = []

    def fake_fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict:
        assert token == "test-token"
        observed_ts_codes.append(f"{api_name}:{params['ts_code']}")
        if api_name == "stock_basic":
            assert fields == "ts_code,symbol,name,industry"
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": ["ts_code", "symbol", "name", "industry"],
                    "items": [
                        ["300502.SZ", "300502", "新易盛", "通信"],
                    ]
                    if params["ts_code"] == "300502.SZ"
                    else [
                        ["300308.SZ", "300308", "中际旭创", "通信"],
                    ],
                },
            }
        assert api_name == "fund_portfolio"
        assert "stk_mkv_ratio" in fields
        if params["ts_code"] == "515880.SH":
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": [
                        "ts_code",
                        "ann_date",
                        "end_date",
                        "symbol",
                        "mkv",
                        "amount",
                        "stk_mkv_ratio",
                        "stk_float_ratio",
                        "stk_code",
                        "stk_name",
                    ],
                    "items": [
                        ["515880.SH", "20250420", "20250331", "300502", 1200000.0, 10000.0, 9.8, 0.6, "300502", "新易盛"],
                        ["515880.SH", "20250420", "20250331", "300308", 1150000.0, 9000.0, 9.1, 0.5, "300308", "中际旭创"],
                        ["515880.SH", "20240120", "20231231", "600519", 900000.0, 8000.0, 8.0, 0.4, "600519", "贵州茅台"],
                    ],
                },
            }
        return {"code": 0, "msg": "", "data": {"fields": [], "items": []}}

    provider = TushareFundHoldingProvider(token="test-token", fetcher=fake_fetcher)

    payload = provider.get_fund_holdings("515880")

    assert observed_ts_codes == [
        "fund_portfolio:515880.SH",
        "stock_basic:300502.SZ",
        "stock_basic:300308.SZ",
    ]
    assert payload["as_of_date"] == "2025-03-31"
    assert payload["fund"]["fund_code"] == "515880"
    assert payload["fund"]["provider_metadata"]["provider_name"] == "tushare-fund-portfolio"
    assert payload["fund"]["provider_metadata"]["data_quality"] == "fresh"
    assert payload["holdings"] == [
        {
            "stock_code": "300502",
            "stock_name": "新易盛",
            "weight": 0.098,
            "holding_change": 0.0,
            "industry": "通信",
        },
        {
            "stock_code": "300308",
            "stock_name": "中际旭创",
            "weight": 0.091,
            "holding_change": 0.0,
            "industry": "通信",
        },
    ]


def test_tushare_holdings_provider_tries_sz_before_of_for_lof_codes():
    observed_ts_codes: list[str] = []

    def fake_fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict:
        observed_ts_codes.append(f"{api_name}:{params['ts_code']}")
        if api_name == "stock_basic":
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": ["ts_code", "symbol", "name", "industry"],
                    "items": [["600519.SH", "600519", "贵州茅台", "食品饮料"]],
                },
            }
        if params["ts_code"] == "161725.SZ":
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": [
                        "ts_code",
                        "ann_date",
                        "end_date",
                        "symbol",
                        "mkv",
                        "amount",
                        "stk_mkv_ratio",
                        "stk_float_ratio",
                        "stk_code",
                        "stk_name",
                    ],
                    "items": [
                        ["161725.SZ", "20250420", "20250331", "600519", 1200000.0, 10000.0, 11.2, 0.6, "600519", "贵州茅台"]
                    ],
                },
            }
        return {"code": 0, "msg": "", "data": {"fields": [], "items": []}}

    provider = TushareFundHoldingProvider(token="test-token", fetcher=fake_fetcher)
    payload = provider.get_fund_holdings("161725")

    assert payload["holdings"][0]["stock_code"] == "600519"
    assert observed_ts_codes == [
        "fund_portfolio:161725.SZ",
        "stock_basic:600519.SH",
    ]
