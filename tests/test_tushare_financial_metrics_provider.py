from src import local_env
from src.providers.tushare_financials import TushareFinancialMetricsProvider


def test_tushare_financial_metrics_provider_returns_unavailable_without_token(
    monkeypatch,
):
    monkeypatch.setattr(local_env, "get_config_value", lambda name: None)
    provider = TushareFinancialMetricsProvider(token=None)

    payload = provider.get_financial_metrics(["600519"])

    assert payload["provider_name"] == "tushare-financial-metrics"
    assert payload["data_quality"] == "unavailable"
    assert payload["metrics"] == []
    assert payload["missing_stock_codes"] == ["600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"
    assert "TUSHARE_TOKEN" in provider.degradation_events[-1]["reason"]


def test_tushare_financial_metrics_provider_maps_income_and_indicator_rows():
    def fake_fetcher(
        token: str,
        params: dict[str, object],
        fields: str,
        api_name: str,
    ) -> dict:
        assert token == "test-token"
        assert params == {"ts_code": "600519.SH"}
        if api_name == "income":
            assert "total_revenue" in fields
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": [
                        "ts_code",
                        "ann_date",
                        "end_date",
                        "report_type",
                        "total_revenue",
                        "n_income_attr_p",
                    ],
                    "items": [
                        ["600519.SH", "20250429", "20250331", "一季报", 51400000000.0, 24800000000.0]
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
        assert api_name == "fina_indicator"
        return {
            "code": 0,
            "msg": "",
            "data": {
                "fields": [
                    "ts_code",
                    "ann_date",
                    "end_date",
                    "q_roe",
                    "grossprofit_margin",
                    "debt_to_assets",
                    "tr_yoy",
                    "netprofit_yoy",
                    "dt_netprofit_yoy",
                ],
                "items": [
                    ["600519.SH", "20250429", "20250331", 10.57, 91.23, 12.12, 6.33, 1.47, 1.45]
                ],
            },
        }

    provider = TushareFinancialMetricsProvider(token="test-token", fetcher=fake_fetcher)

    payload = provider.get_financial_metrics(["600519"])

    assert payload["provider_name"] == "tushare-financial-metrics"
    assert payload["data_quality"] == "fresh"
    assert payload["missing_stock_codes"] == []
    assert payload["metrics"][0]["stock_code"] == "600519"
    assert payload["metrics"][0]["stock_name"] == "贵州茅台"
    assert payload["metrics"][0]["report_date"] == "2025-03-31"
    assert payload["metrics"][0]["report_type"] == "一季报"
    assert payload["metrics"][0]["notice_date"] == "2025-04-29"
    assert payload["metrics"][0]["revenue"] == 51400000000.0
    assert payload["metrics"][0]["revenue_yoy"] == 6.33
    assert payload["metrics"][0]["parent_net_profit"] == 24800000000.0
    assert payload["metrics"][0]["parent_net_profit_yoy"] == 1.47
    assert payload["metrics"][0]["deduct_parent_net_profit_yoy"] == 1.45
    assert payload["metrics"][0]["roe"] == 10.57
    assert payload["metrics"][0]["gross_margin"] == 91.23
    assert payload["metrics"][0]["debt_asset_ratio"] == 12.12


def test_tushare_financial_metrics_provider_prefers_local_env_token(monkeypatch):
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
        if api_name == "income":
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": [
                        "ts_code",
                        "ann_date",
                        "end_date",
                        "report_type",
                        "total_revenue",
                        "n_income_attr_p",
                    ],
                    "items": [
                        ["600519.SH", "20250429", "20250331", "一季报", 1.0, 2.0]
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
        assert api_name == "fina_indicator"
        return {
            "code": 0,
            "msg": "",
            "data": {
                "fields": [
                    "ts_code",
                    "ann_date",
                    "end_date",
                    "q_roe",
                    "grossprofit_margin",
                    "debt_to_assets",
                    "tr_yoy",
                    "netprofit_yoy",
                    "dt_netprofit_yoy",
                ],
                "items": [
                    ["600519.SH", "20250429", "20250331", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
                ],
            },
        }

    provider = TushareFinancialMetricsProvider(fetcher=fake_fetcher)
    provider.get_financial_metrics(["600519"])

    assert observed_tokens == ["local-token", "local-token", "local-token"]
