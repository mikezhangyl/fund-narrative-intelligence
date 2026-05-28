from __future__ import annotations

import json

from scripts import run_sector_scan


class FakeSectorSource:
    def fetch_sector_data(self, trade_date):
        raise RuntimeError("sector endpoint blocked")

    def fetch_etf_data(self, symbols, start_date, end_date):
        return [
            {
                "symbol": symbol,
                "trade_date": end_date,
                "pct_change": 1.0,
                "amount": 10.0,
            }
            for symbol in symbols
        ]


def test_sector_scan_cli_writes_partial_report(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_sector_scan,
        "ConsolidatedMarketDataSource",
        lambda: FakeSectorSource(),
    )

    exit_code = run_sector_scan.main(
        [
            "--trade-date",
            "2026-05-22",
            "--etf-symbols",
            "510300.SH,159915.SZ",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "sector_scan_report.json").read_text())

    assert exit_code == 0
    assert payload["result"]["status"] == "partial"
    assert payload["result"]["etf_count"] == 2
    assert "sector endpoint blocked" in (
        tmp_path / "sector_scan_report.md"
    ).read_text()
