from __future__ import annotations

from src.market_data.fallback import FallbackMarketDataProvider
from src.market_data.validators import validate_records


class FailingProvider:
    provider_name = "primary"

    def fetch_daily_bars(self, **kwargs):
        raise RuntimeError("rate limited")

    def health_check(self):
        return {"provider": "primary", "ok": False}


class WorkingProvider:
    provider_name = "fallback"

    def fetch_daily_bars(self, **kwargs):
        return [{"symbol": "600519.SH", "trade_date": "2026-05-22"}]

    def health_check(self):
        return {"provider": "fallback", "ok": True}


def test_fallback_provider_uses_secondary_after_primary_failure():
    provider = FallbackMarketDataProvider(
        primary=FailingProvider(),
        fallback=WorkingProvider(),
    )

    rows = provider.fetch_daily_bars(
        symbols=["600519.SH"],
        start_date="20260522",
        end_date="20260522",
    )

    assert rows[0]["symbol"] == "600519.SH"
    assert provider.degradation_events == [
        {
            "type": "provider_fallback",
            "primary_provider": "primary",
            "fallback_provider": "fallback",
            "reason": "rate limited",
        }
    ]


def test_validate_records_reports_completeness_and_schema_stability():
    result = validate_records(
        source="tushare",
        endpoint="daily",
        records=[{"symbol": "600519.SH", "trade_date": "2026-05-22"}],
        required_fields={"symbol", "trade_date", "close"},
        expected_schema_fingerprint="wrong",
        latency_ms=12.5,
    )

    assert result.availability is True
    assert result.latency_ms == 12.5
    assert result.completeness is False
    assert result.schema_stability is False
    assert result.missing_fields == ["close"]
