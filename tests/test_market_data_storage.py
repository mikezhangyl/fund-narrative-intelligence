from __future__ import annotations

import builtins

import pytest
from src.storage.parquet_store import ParquetStore
from src.storage.postgres import PostgresStore, PostgresStoreUnavailable


def test_parquet_store_uses_csv_fallback_when_pyarrow_is_unavailable(
    tmp_path,
    monkeypatch,
):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("pyarrow"):
            raise ImportError("missing pyarrow")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    path = ParquetStore(root_dir=tmp_path).write_rows(
        dataset="daily_bars",
        rows=[{"symbol": "600519.SH", "close": 1560.0}],
    )

    assert path.name == "daily_bars.csv"
    assert "600519.SH" in path.read_text(encoding="utf-8")


def test_postgres_store_reports_missing_driver_or_dsn(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(PostgresStoreUnavailable):
        PostgresStore().connect()
