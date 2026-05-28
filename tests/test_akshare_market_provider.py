from src.providers.akshare_market import AkshareMarketDataProvider


class _FakeFrame:
    def __init__(self, rows):
        self._rows = rows

    def to_dict(self, orient: str):
        assert orient == "records"
        return self._rows


def test_akshare_market_provider_returns_unavailable_when_client_missing():
    provider = AkshareMarketDataProvider(client_loader=lambda: None)

    payload = provider.get_stock_quotes(["600519", "000858"])

    assert payload["provider_name"] == "akshare-market-quote"
    assert payload["data_quality"] == "unavailable"
    assert payload["quotes"] == []
    assert payload["missing_stock_codes"] == ["000858", "600519"]
    assert provider.degradation_events[-1]["type"] == "provider_unavailable"


def test_akshare_market_provider_maps_history_rows():
    class FakeAkshareClient:
        def stock_zh_a_hist(
            self,
            symbol: str,
            period: str,
            start_date: str,
            end_date: str,
            adjust: str,
        ):
            assert symbol == "600519"
            assert period == "daily"
            assert len(start_date) == 8
            assert len(end_date) == 8
            assert adjust == ""
            return _FakeFrame(
                [
                    {
                        "日期": "2025-05-15",
                        "股票代码": "600519",
                        "股票名称": "贵州茅台",
                        "开盘": 1550.0,
                        "收盘": 1560.0,
                        "最高": 1568.0,
                        "最低": 1544.0,
                        "成交量": 123456.0,
                        "成交额": 987654321.0,
                        "涨跌幅": 1.96,
                        "涨跌额": 30.0,
                        "换手率": 0.42,
                    }
                ]
            )

    provider = AkshareMarketDataProvider(client=FakeAkshareClient())

    payload = provider.get_stock_quotes(["600519"])

    assert payload["provider_name"] == "akshare-market-quote"
    assert payload["data_quality"] == "fresh"
    assert payload["missing_stock_codes"] == []
    assert payload["quotes"][0]["stock_code"] == "600519"
    assert payload["quotes"][0]["stock_name"] == "贵州茅台"
    assert payload["quotes"][0]["latest_price"] == 1560.0
    assert payload["quotes"][0]["change_amount"] == 30.0
    assert payload["quotes"][0]["previous_close"] == 1530.0
