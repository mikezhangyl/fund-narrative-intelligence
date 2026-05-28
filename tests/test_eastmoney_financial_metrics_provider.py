from urllib.error import URLError

from src.providers.eastmoney_financials import (
    EASTMONEY_FINANCIAL_METRICS_URL,
    EastmoneyFinancialMetricsProvider,
    build_eastmoney_financial_metrics_url,
    normalize_eastmoney_financial_metrics_response,
)


def test_builds_eastmoney_financial_metrics_url():
    url = build_eastmoney_financial_metrics_url("600519")

    assert url.startswith(EASTMONEY_FINANCIAL_METRICS_URL)
    assert "RPT_F10_FINANCE_MAINFINADATA" in url
    assert "APP_F10_MAINFINADATA" in url
    assert "600519.SH" in url


def test_normalizes_eastmoney_financial_metrics_response():
    payload = normalize_eastmoney_financial_metrics_response(
        response={
            "result": {
                "data": [
                    {
                        "SECUCODE": "600519.SH",
                        "SECURITY_CODE": "600519",
                        "SECURITY_NAME_ABBR": "贵州茅台",
                        "REPORT_DATE": "2026-03-31 00:00:00",
                        "REPORT_TYPE": "一季报",
                        "NOTICE_DATE": "2026-04-25 00:00:00",
                        "CURRENCY": "CNY",
                        "TOTALOPERATEREVE": 54702912385.23,
                        "TOTALOPERATEREVETZ": 6.336,
                        "PARENTNETPROFIT": 27242512886.45,
                        "PARENTNETPROFITTZ": 1.4714,
                        "KCFJCXSYJLRTZ": 1.4529,
                        "ROEJQ": 10.57,
                        "XSMLL": 89.7592,
                        "XSJLL": 52.2245,
                        "ZCFZL": 12.1227,
                    }
                ]
            }
        },
        requested_stock_codes=["600519", "000858"],
        source_url="https://example.test/financials",
        retrieved_at="2026-05-15T00:00:00+00:00",
    )

    assert payload["version"] == "financial-metrics-v1"
    assert payload["provider_name"] == "eastmoney-financial-metrics"
    assert payload["data_quality"] == "partial"
    assert payload["metrics"][0]["stock_code"] == "600519"
    assert payload["metrics"][0]["revenue_yoy"] == 6.336
    assert payload["metrics"][0]["parent_net_profit_yoy"] == 1.4714
    assert payload["missing_stock_codes"] == ["000858"]


def test_eastmoney_financial_metrics_provider_returns_unavailable_without_crashing():
    def failing_fetcher(_url: str) -> dict:
        raise URLError("network unavailable")

    provider = EastmoneyFinancialMetricsProvider(fetcher=failing_fetcher)

    payload = provider.get_financial_metrics(["600519"])

    assert payload["provider_name"] == "eastmoney-financial-metrics"
    assert payload["data_quality"] == "unavailable"
    assert payload["metrics"] == []
    assert payload["missing_stock_codes"] == ["600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"


def test_eastmoney_financial_metrics_provider_marks_hong_kong_stock_as_unsupported():
    provider = EastmoneyFinancialMetricsProvider()

    payload = provider.get_financial_metrics(["00700"])

    assert payload["provider_name"] == "eastmoney-financial-metrics"
    assert payload["data_quality"] == "unavailable"
    assert payload["metrics"] == []
    assert payload["missing_stock_codes"] == ["00700"]
    assert provider.degradation_events[-1]["type"] == "provider_unsupported_market"
