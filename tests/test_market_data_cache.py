from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.market_data.cache import FileSystemMarketDataCache


def test_file_system_cache_round_trips_payload_and_avoids_duplicate_fetch(tmp_path):
    cache = FileSystemMarketDataCache(root_dir=tmp_path)
    calls = 0

    def fetch_payload() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"rows": [{"symbol": "600519.SH", "close": 1560.0}]}

    first = cache.get_or_set(
        namespace="tushare.daily",
        key_parts={"ts_code": "600519.SH", "trade_date": "20260522"},
        loader=fetch_payload,
    )
    second = cache.get_or_set(
        namespace="tushare.daily",
        key_parts={"trade_date": "20260522", "ts_code": "600519.SH"},
        loader=fetch_payload,
    )

    assert first == second
    assert calls == 1


def test_file_system_cache_honors_max_age(tmp_path):
    cache = FileSystemMarketDataCache(root_dir=tmp_path)
    cache.set(
        namespace="akshare.endpoint",
        key_parts={"endpoint": "stock_board_concept_name_em"},
        payload={"rows": []},
        created_at=datetime.now(UTC) - timedelta(days=2),
    )

    assert (
        cache.get(
            namespace="akshare.endpoint",
            key_parts={"endpoint": "stock_board_concept_name_em"},
            max_age_seconds=60,
        )
        is None
    )
