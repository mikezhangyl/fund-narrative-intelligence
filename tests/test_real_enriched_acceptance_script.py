import json
from pathlib import Path

import pytest
from scripts import validate_real_enriched_acceptance


def test_real_enriched_acceptance_script_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_real_enriched_outputs(tmp_path)
        return 0

    monkeypatch.setattr(validate_real_enriched_acceptance.pipeline_main, "main", fake_main)

    exit_code = validate_real_enriched_acceptance.main(["--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Real enriched acceptance passed:" in captured.out
    assert calls == [
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-cninfo-announcements",
            "--announcement-start-date",
            "2026-01-01",
            "--include-market-quotes",
            "--output-dir",
            str(tmp_path),
        ],
        ["--validate-artifact-contracts", str(tmp_path)],
    ]


def test_real_enriched_acceptance_rejects_missing_market_quote_signals(tmp_path):
    _write_real_enriched_outputs(tmp_path, include_market_quote_signal=False)

    with pytest.raises(validate_real_enriched_acceptance.AcceptanceError) as exc:
        validate_real_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "derived signals must include market_quote" in str(exc.value)


def test_real_enriched_acceptance_rejects_hidden_disclosure(tmp_path):
    _write_real_enriched_outputs(tmp_path, disclosure_required=False)

    with pytest.raises(validate_real_enriched_acceptance.AcceptanceError) as exc:
        validate_real_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "provider foundation must require disclosure" in str(exc.value)


def test_real_enriched_acceptance_rejects_unexpected_degradation(tmp_path):
    _write_real_enriched_outputs(
        tmp_path,
        degradation_events=[
            {
                "type": "provider_failure",
                "provider": "cninfo-announcement",
                "reason": "timeout",
            }
        ],
    )

    with pytest.raises(validate_real_enriched_acceptance.AcceptanceError) as exc:
        validate_real_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "unexpected degradation event" in str(exc.value)


def test_real_enriched_acceptance_rejects_missing_quote_coverage(tmp_path):
    _write_real_enriched_outputs(tmp_path, missing_quote_stock_codes=["000858"])

    with pytest.raises(validate_real_enriched_acceptance.AcceptanceError) as exc:
        validate_real_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "market quotes must not miss requested stock codes" in str(exc.value)


def _write_real_enriched_outputs(
    output_dir: Path,
    include_market_quote_signal: bool = True,
    disclosure_required: bool = True,
    degradation_events: list[dict] | None = None,
    missing_quote_stock_codes: list[str] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    degradation_events = degradation_events or []
    missing_quote_stock_codes = missing_quote_stock_codes or []
    announcement_signal = {
        "signal_id": "SIG_ANN_cninfo-600519-0",
        "narrative_id": "premium_baijiu_consumption",
        "signal_type": "management_mentions_up",
        "strength": 0.18,
        "confidence": 0.3,
        "confidence_multiplier": 0.55,
        "event_date": "2026-03-15",
        "half_life_days": 30,
        "source": "cninfo_announcement",
        "source_evidence_id": "cninfo-600519-0",
        "source_url": "https://static.cninfo.com.cn/fake.pdf",
        "derivation_reason": "mixed financial disclosure announcement evidence",
    }
    market_signal = {
        "signal_id": "SIG_QUOTE_600519_premium_baijiu_consumption",
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
    derived_signal_events = [announcement_signal]
    if include_market_quote_signal:
        derived_signal_events.append(market_signal)
    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": disclosure_required,
        "disclosure_message": (
            "混合数据源：Holdings 来自 Eastmoney；Announcements 来自 CNINFO；"
            "Market Quotes 来自 yahoo-chart；Evidence 使用 Mock fixtures。"
        ),
        "layers": {
            "holdings": _real_layer("holdings", "eastmoney-fundmobapi", "Eastmoney"),
            "narrative_registry": _mock_layer("narrative_registry"),
            "stock_mappings": _mock_layer("stock_mappings"),
            "evidence": _mock_layer("evidence"),
            "signals": _mock_layer("signals"),
            "announcements": _real_layer("announcements", "cninfo-announcement", "CNINFO"),
            "market_quotes": _real_layer("market_quotes", "yahoo-chart", "Market Quotes"),
            "derived_signals": _real_layer(
                "derived_signals",
                "mixed-derived-signals",
                "Derived Signals",
            ),
        },
        "degradation_events": degradation_events,
    }
    fund = {
        "fund_code": "161725",
        "provider_metadata": {
            "provider_name": "eastmoney-fundmobapi",
            "provider_version": "eastmoney-v1",
            "data_quality": "fresh",
            "source_url": "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition?FCODE=161725",
        },
    }
    market_quotes = {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "yahoo-chart",
        "provider_version": "yahoo-chart-v1",
        "data_quality": "fresh",
        "source_url": "multiple://market-quotes",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "quotes": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "source_provider": "yahoo-chart",
                "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
                "change_percent": 2.0,
            }
        ],
        "missing_stock_codes": missing_quote_stock_codes,
    }
    announcement_evidence = {
        "version": "announcement-evidence-v1",
        "data_quality": "fresh",
        "evidence": [
            {
                "evidence_id": "cninfo-600519-0",
                "narrative_id": "premium_baijiu_consumption",
                "source": "cninfo_announcement",
                "source_url": "https://static.cninfo.com.cn/fake.pdf",
                "sentiment": "mixed",
            }
        ],
        "skipped_announcement_count": 0,
    }
    raw = {
        "metadata": {"fund_code": "161725", "as_of_date": "2026-03-31", "data_quality": "partial"},
        "fund": fund,
        "provider_foundation": provider_foundation,
        "announcements": {
            "version": "cninfo-announcement-v1",
            "data_quality": "fresh",
            "announcements": [{"stock_code": "600519", "title": "年度报告"}],
            "missing_stock_codes": [],
        },
        "announcement_evidence": announcement_evidence,
        "market_quotes": market_quotes,
        "derived_signal_events": derived_signal_events,
        "signal_events": derived_signal_events,
        "degradation_events": degradation_events,
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": fund,
        "provider_foundation": provider_foundation,
        "announcement_evidence": announcement_evidence,
        "market_quotes": market_quotes,
        "derived_signal_events": derived_signal_events,
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {"total_count": 0, "pending_count": 0, "action_required": False},
            "items": [],
        },
        "degradation_events": degradation_events,
    }
    review_queue = {
        "metadata": raw["metadata"],
        "fund": fund,
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
        "degradation_events": degradation_events,
        "artifacts": {
            "raw": {"path": "fund_161725_raw.json", "format": "json"},
            "scoring": {"path": "fund_161725_scoring.json", "format": "json"},
            "review_queue": {"path": "fund_161725_review_queue.json", "format": "json"},
            "markdown": {"path": "fund_161725_report.md", "format": "markdown"},
            "html": {"path": "fund_161725_report.html", "format": "html"},
        },
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_review_queue.json", review_queue)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    notice = (
        "Data Source Notice\n混合数据源\nEastmoney\nCNINFO\nMarket Quotes\n"
        "Derived Signals\nMock fixtures\n"
    )
    (output_dir / "fund_161725_report.md").write_text(notice, encoding="utf-8")
    (output_dir / "fund_161725_report.html").write_text(notice, encoding="utf-8")


def _real_layer(layer: str, provider_name: str, display_name: str) -> dict:
    source_urls = {
        "holdings": "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition?FCODE=161725",
        "announcements": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
        "market_quotes": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
        "derived_signals": "derived://mixed-derived-signals",
    }
    return {
        "layer": layer,
        "display_name": display_name,
        "provider_name": provider_name,
        "provider_version": "real-v1",
        "data_quality": "fresh",
        "source_url": source_urls[layer],
        "is_mock": False,
        "note": "Real provider layer.",
    }


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
