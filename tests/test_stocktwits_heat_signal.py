from __future__ import annotations

import json

from scripts import run_stocktwits_heat_signal_smoke
from src.scanners.stocktwits_heat_signal import (
    StocktwitsHeatSignalProvider,
    render_stocktwits_heat_signal_html,
)


def test_stocktwits_provider_normalizes_fixture_messages_as_heat_only():
    payload = StocktwitsHeatSignalProvider(fetcher=lambda _url, _timeout: _stocktwits_fixture()).get_heat_signals(
        symbols=["AAPL"],
        limit=2,
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    assert payload["version"] == "stocktwits-heat-signal-v1"
    assert payload["summary"] == {
        "requested_symbol_count": 1,
        "message_count": 2,
        "degradation_count": 0,
        "heat_trust_tier": "heat_signal_only",
    }
    assert payload["request_policy"] == {
        "enabled_by_default": False,
        "timeout_seconds": 10,
        "cache_ttl_seconds": 300,
        "rate_limit_policy": "bounded_symbol_smoke_only",
    }
    first = payload["events"][0]
    assert first["source_type"] == "social"
    assert first["provider"] == "stocktwits-symbol-stream"
    assert first["heat_trust_tier"] == "heat_signal_only"
    assert first["trust_status"] == "candidate_untrusted"
    assert first["stock_codes"] == ["AAPL"]
    assert first["source_metadata"]["message_id"] == "1001"
    assert first["source_metadata"]["user_id"] == "501"
    assert first["source_metadata"]["username"] == "marketwatcher"
    assert first["source_metadata"]["body_excerpt"] == "AAPL supply chain discussion is heating up around AI devices."
    assert first["source_metadata"]["heat_trust_tier"] == "heat_signal_only"
    assert first["source_url"] == "https://stocktwits.com/marketwatcher/message/1001"
    assert "trusted_fact" not in json.dumps(payload, ensure_ascii=False)


def test_stocktwits_provider_returns_degradation_on_failure():
    def failing_fetcher(_url: str, _timeout: int) -> dict[str, object]:
        raise TimeoutError("stocktwits timeout")

    payload = StocktwitsHeatSignalProvider(fetcher=failing_fetcher).get_heat_signals(
        symbols=["AAPL"],
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    assert payload["data_quality"] == "unavailable"
    assert payload["events"] == []
    assert payload["degradation_events"] == [
        {
            "type": "provider_unavailable",
            "provider_name": "stocktwits-symbol-stream",
            "symbol": "AAPL",
            "reason": "Stocktwits fetch failed for AAPL: stocktwits timeout",
        }
    ]


def test_stocktwits_empty_response_is_structured_not_silent_success():
    payload = StocktwitsHeatSignalProvider(fetcher=lambda _url, _timeout: {"messages": []}).get_heat_signals(
        symbols=["AAPL"],
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    assert payload["data_quality"] == "empty"
    assert payload["summary"]["message_count"] == 0
    assert payload["degradation_events"][0]["type"] == "empty_response"


def test_stocktwits_heat_signal_html_is_chinese_and_heat_only():
    payload = StocktwitsHeatSignalProvider(fetcher=lambda _url, _timeout: _stocktwits_fixture()).get_heat_signals(
        symbols=["AAPL"],
        limit=1,
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    html = render_stocktwits_heat_signal_html(payload)

    assert "<h1>Stocktwits 热度信号试点</h1>" in html
    assert "heat_signal_only" in html
    assert "不能作为 trusted evidence" in html
    assert "marketwatcher" in html


def test_stocktwits_heat_signal_smoke_cli_writes_json_and_html(tmp_path):
    input_path = tmp_path / "stocktwits.json"
    input_path.write_text(json.dumps(_stocktwits_fixture()), encoding="utf-8")
    output_dir = tmp_path / "out"

    exit_code = run_stocktwits_heat_signal_smoke.main(
        [
            "--symbol",
            "AAPL",
            "--limit",
            "2",
            "--input-json",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads((output_dir / "stocktwits_heat_signal.json").read_text())
    html = (output_dir / "stocktwits_heat_signal.html").read_text()

    assert payload["summary"]["message_count"] == 2
    assert {event["heat_trust_tier"] for event in payload["events"]} == {"heat_signal_only"}
    assert "<h1>Stocktwits 热度信号试点</h1>" in html


def _stocktwits_fixture() -> dict[str, object]:
    return {
        "messages": [
            {
                "id": 1001,
                "body": "AAPL supply chain discussion is heating up around AI devices.",
                "created_at": "2026-05-31T15:00:00Z",
                "user": {"id": 501, "username": "marketwatcher"},
                "symbols": [{"symbol": "AAPL", "title": "Apple Inc."}],
            },
            {
                "id": 1002,
                "body": "Watching AAPL volume into the close; social chatter only.",
                "created_at": "2026-05-31T15:05:00Z",
                "user": {"id": 502, "username": "heatreader"},
                "symbols": [{"symbol": "AAPL", "title": "Apple Inc."}],
            },
        ]
    }
