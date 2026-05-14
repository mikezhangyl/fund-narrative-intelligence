import json
from pathlib import Path

import pytest
from scripts import validate_market_quotes_acceptance


def test_market_quotes_acceptance_script_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_market_quote_outputs(tmp_path)
        return 0

    monkeypatch.setattr(validate_market_quotes_acceptance.pipeline_main, "main", fake_main)

    exit_code = validate_market_quotes_acceptance.main(["--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Market quotes acceptance passed:" in captured.out
    assert calls == [
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-market-quotes",
            "--output-dir",
            str(tmp_path),
        ],
        ["--validate-artifact-contracts", str(tmp_path)],
    ]


def test_market_quotes_acceptance_rejects_unavailable_quotes(tmp_path):
    _write_market_quote_outputs(tmp_path, quote_count=0, market_quality="unavailable")

    with pytest.raises(validate_market_quotes_acceptance.AcceptanceError) as exc:
        validate_market_quotes_acceptance.validate_acceptance_outputs(tmp_path)

    assert "market quotes data_quality must be fresh or partial" in str(exc.value)


def _write_market_quote_outputs(
    output_dir: Path,
    quote_count: int = 2,
    market_quality: str = "fresh",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    quotes = [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "source_provider": "yahoo-chart",
            "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
            "latest_price": 1342.17,
            "change_percent": 2.0,
            "change_amount": -1.92,
            "volume": 55244,
            "amount": None,
            "high": 1369.06,
            "low": 1335.18,
            "open": 1338.0,
            "previous_close": 1344.09,
            "retrieved_at": "2026-05-14T00:00:00+00:00",
        }
        for _ in range(quote_count)
    ]
    market_quotes = {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "yahoo-chart" if market_quality != "unavailable" else "eastmoney-market-quote",
        "provider_version": "yahoo-chart-v1" if market_quality != "unavailable" else "eastmoney-market-quote-v1",
        "data_quality": market_quality,
        "source_url": "multiple://market-quotes",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "quotes": quotes,
        "missing_stock_codes": [] if quotes else ["600519"],
    }
    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": True,
        "disclosure_message": (
            "混合数据源：Holdings 来自 Eastmoney；Market Quotes 来自 yahoo-chart；"
            "Evidence 使用 Mock fixtures。"
        ),
        "layers": {
            "holdings": {
                "layer": "holdings",
                "display_name": "Holdings",
                "provider_name": "eastmoney-fundmobapi",
                "provider_version": "eastmoney-v1",
                "data_quality": "fresh",
                "source_url": (
                    "https://fundmobapi.eastmoney.com/FundMNewApi/"
                    "FundMNInverstPosition?FCODE=161725"
                ),
                "is_mock": False,
                "note": "Fund holdings fetched from Eastmoney.",
            },
            "narrative_registry": _mock_layer("narrative_registry"),
            "stock_mappings": _mock_layer("stock_mappings"),
            "evidence": _mock_layer("evidence"),
            "signals": _mock_layer("signals"),
            "derived_signals": {
                "layer": "derived_signals",
                "display_name": "Derived Signals",
                "provider_name": "market-quote-derived-signals",
                "provider_version": "derived-signals-v1",
                "data_quality": market_quality,
                "source_url": "derived://market-quote-derived-signals",
                "is_mock": False,
                "note": "Derived from real market quote snapshots.",
            },
            "market_quotes": {
                "layer": "market_quotes",
                "display_name": "Market Quotes",
                "provider_name": market_quotes["provider_name"],
                "provider_version": market_quotes["provider_version"],
                "data_quality": market_quality,
                "source_url": market_quotes["source_url"],
                "is_mock": False,
                "note": "Optional market quote snapshot.",
            },
        },
        "degradation_events": [],
    }
    derived_signal_events = [
        {
            "signal_id": f"SIG_QUOTE_600519_premium_baijiu_consumption_{index}",
            "narrative_id": "premium_baijiu_consumption",
            "signal_type": "relative_strength_up",
            "strength": 0.4,
            "confidence": 0.44,
            "confidence_multiplier": 0.65,
            "event_date": "2026-05-14",
            "half_life_days": 10,
            "source": "market_quote",
            "source_provider": "yahoo-chart",
            "source_stock_code": "600519",
            "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
            "derivation_reason": "positive market quote change percent",
        }
        for index in range(quote_count)
    ]
    raw = {
        "metadata": {
            "fund_code": "161725",
            "as_of_date": "2026-03-31",
            "data_quality": "partial",
        },
        "fund": {
            "fund_code": "161725",
            "provider_metadata": {
                "provider_name": "eastmoney-fundmobapi",
                "provider_version": "eastmoney-v1",
                "data_quality": "fresh",
                "source_url": (
                    "https://fundmobapi.eastmoney.com/FundMNewApi/"
                    "FundMNInverstPosition?FCODE=161725"
                ),
            },
        },
        "provider_foundation": provider_foundation,
        "market_quotes": market_quotes,
        "signal_events": derived_signal_events,
        "derived_signal_events": derived_signal_events,
        "degradation_events": [],
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": raw["fund"],
        "provider_foundation": provider_foundation,
        "market_quotes": market_quotes,
        "derived_signal_events": derived_signal_events,
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {"total_count": 0, "pending_count": 0, "action_required": False},
            "items": [],
        },
        "degradation_events": [],
    }
    review_queue = {
        "metadata": raw["metadata"],
        "fund": raw["fund"],
        "provider_foundation": provider_foundation,
        "candidate_review_queue": scoring["candidate_review_queue"],
        "candidate_narratives": [],
        "excluded_mapping_candidates": [],
    }
    manifest = {
        "version": "pipeline-artifact-manifest-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_mode": "eastmoney",
        "data_quality": "partial",
        "web_ready": True,
        "provider_foundation": provider_foundation,
        "degradation_events": [],
        "artifacts": {
            "raw": {"path": "fund_161725_raw.json", "format": "json"},
            "scoring": {"path": "fund_161725_scoring.json", "format": "json"},
            "review_queue": {
                "path": "fund_161725_review_queue.json",
                "format": "json",
            },
            "markdown": {"path": "fund_161725_report.md", "format": "markdown"},
            "html": {"path": "fund_161725_report.html", "format": "html"},
        },
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_review_queue.json", review_queue)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    (output_dir / "fund_161725_report.md").write_text(
        "Data Source Notice\n混合数据源\nEastmoney\nMarket Quotes\nyahoo-chart\nMock fixtures\n",
        encoding="utf-8",
    )
    (output_dir / "fund_161725_report.html").write_text(
        "Data Source Notice\n混合数据源\nEastmoney\nMarket Quotes\nyahoo-chart\nMock fixtures\n",
        encoding="utf-8",
    )


def _mock_layer(layer: str) -> dict:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": "mock-fixture-provider",
        "provider_version": "mock-v1",
        "data_quality": "mock",
        "source_url": f"mock://fixtures/{layer}.json",
        "is_mock": True,
        "note": "V1 Mock fixture layer.",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
