import json
from pathlib import Path

import pytest
from scripts import validate_registry_rule_enriched_acceptance


def test_registry_rule_enriched_acceptance_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_outputs(tmp_path)
        return 0

    monkeypatch.setattr(
        validate_registry_rule_enriched_acceptance.pipeline_main,
        "main",
        fake_main,
    )

    exit_code = validate_registry_rule_enriched_acceptance.main(
        ["--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Registry-rule enriched acceptance passed:" in captured.out
    assert calls[0] == [
        "--fund-code",
        "161725",
        "--provider-mode",
        "eastmoney",
        "--stock-mapping-mode",
        "registry-rule",
        "--include-cninfo-announcements",
        "--announcement-start-date",
        "2026-01-01",
        "--include-market-quotes",
        "--output-dir",
        str(tmp_path),
    ]
    assert calls[1] == ["--validate-artifact-contracts", str(tmp_path)]


def test_registry_rule_enriched_acceptance_rejects_fixture_mappings(tmp_path):
    _write_outputs(tmp_path, mapping_method="fixture_rule")

    with pytest.raises(validate_registry_rule_enriched_acceptance.AcceptanceError) as exc:
        validate_registry_rule_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "all selected mappings must use registry_term_rule" in str(exc.value)


def _write_outputs(output_dir: Path, mapping_method: str = "registry_term_rule") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": True,
        "disclosure_message": (
            "混合数据源：Holdings 来自 Eastmoney；Stock Mappings 来自 "
            "registry-rule-stock-mapping；Market Quotes 来自 yahoo-chart；"
            "Announcements 来自 CNINFO；Derived Signals 来自 mixed-derived-signals；"
            "Narrative Registry、Evidence、Signals 使用 Mock fixtures。"
        ),
        "layers": {
            "holdings": _layer("holdings", "eastmoney-fundmobapi", "fresh", False),
            "narrative_registry": _mock_layer("narrative_registry"),
            "stock_mappings": {
                "layer": "stock_mappings",
                "display_name": "Stock Mappings",
                "provider_name": "registry-rule-stock-mapping",
                "provider_version": "stock-mapping-v1",
                "data_quality": "partial",
                "source_url": "derived://registry-term-rule-stock-mapping",
                "is_mock": False,
                "note": "Runtime mappings.",
            },
            "evidence": _mock_layer("evidence"),
            "signals": _mock_layer("signals"),
            "announcements": _layer("announcements", "cninfo-announcement", "fresh", False),
            "market_quotes": _layer("market_quotes", "yahoo-chart", "fresh", False),
            "derived_signals": _layer(
                "derived_signals", "mixed-derived-signals", "fresh", False
            ),
        },
        "degradation_events": [],
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
    announcement_evidence = {
        "version": "announcement-evidence-v1",
        "data_quality": "fresh",
        "evidence": [
            {
                "evidence_id": "cninfo-600519-0",
                "narrative_id": "premium_baijiu_consumption",
                "source": "cninfo_announcement",
                "source_url": "https://static.cninfo.com.cn/fake.pdf",
            }
        ],
    }
    market_quotes = {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "yahoo-chart",
        "data_quality": "fresh",
        "quotes": [
            {
                "stock_code": "600519",
                "source_provider": "yahoo-chart",
                "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
            }
        ],
        "missing_stock_codes": [],
    }
    derived_signal_events = [
        {
            "signal_id": "SIG_ANN_cninfo-600519-0",
            "source": "cninfo_announcement",
        },
        {
            "signal_id": "SIG_QUOTE_600519_premium_baijiu_consumption",
            "source": "market_quote",
        },
    ]
    raw = {
        "metadata": {"fund_code": "161725", "data_quality": "partial"},
        "fund": fund,
        "provider_foundation": provider_foundation,
        "stock_mapping_mode": "registry-rule",
        "stock_narrative_mappings": [
            {
                "stock_code": "600519",
                "narrative_id": "premium_baijiu_consumption",
                "method": mapping_method,
            }
        ],
        "mapping_coverage": {"mapping_methods": {mapping_method: 1}},
        "announcements": {
            "version": "cninfo-announcement-v1",
            "data_quality": "fresh",
            "announcements": [{"stock_code": "600519"}],
            "missing_stock_codes": [],
        },
        "announcement_evidence": announcement_evidence,
        "market_quotes": market_quotes,
        "derived_signal_events": derived_signal_events,
        "signal_events": derived_signal_events,
        "degradation_events": [],
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": fund,
        "provider_foundation": provider_foundation,
        "stock_mapping_mode": "registry-rule",
        "stock_narrative_mappings": raw["stock_narrative_mappings"],
        "mapping_coverage": raw["mapping_coverage"],
        "announcement_evidence": announcement_evidence,
        "market_quotes": market_quotes,
        "derived_signal_events": derived_signal_events,
        "candidate_review_queue": {"version": "candidate-review-queue-v1"},
        "degradation_events": [],
    }
    review_queue = {
        "metadata": raw["metadata"],
        "fund": fund,
        "provider_foundation": provider_foundation,
        "candidate_review_queue": scoring["candidate_review_queue"],
    }
    manifest = {
        "provider_mode": "eastmoney",
        "data_quality": "partial",
        "provider_foundation": provider_foundation,
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_review_queue.json", review_queue)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    notice = (
        "混合数据源\nEastmoney\nCNINFO\nMarket Quotes\nDerived Signals\n"
        "Stock Mappings\nregistry-rule-stock-mapping\nMock fixtures\n"
    )
    (output_dir / "fund_161725_report.md").write_text(notice, encoding="utf-8")
    (output_dir / "fund_161725_report.html").write_text(notice, encoding="utf-8")


def _layer(layer: str, provider_name: str, data_quality: str, is_mock: bool) -> dict:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": provider_name,
        "provider_version": "real-v1",
        "data_quality": data_quality,
        "source_url": _source_url(layer),
        "is_mock": is_mock,
        "note": "",
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
        "note": "",
    }


def _source_url(layer: str) -> str:
    return {
        "holdings": "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition?FCODE=161725",
        "announcements": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
        "market_quotes": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
        "derived_signals": "derived://mixed-derived-signals",
    }[layer]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
