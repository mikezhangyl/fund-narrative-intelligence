import json
from pathlib import Path

import pytest
from scripts import validate_reviewed_registry_enriched_acceptance


def test_reviewed_registry_enriched_acceptance_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text("{}", encoding="utf-8")

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_outputs(tmp_path)
        return 0

    monkeypatch.setattr(
        validate_reviewed_registry_enriched_acceptance.pipeline_main,
        "main",
        fake_main,
    )

    exit_code = validate_reviewed_registry_enriched_acceptance.main(
        [
            "--narrative-registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Reviewed-registry enriched acceptance passed:" in captured.out
    assert calls[0] == [
        "--fund-code",
        "161725",
        "--provider-mode",
        "eastmoney",
        "--narrative-registry-mode",
        "reviewed",
        "--narrative-registry-path",
        str(registry_path),
        "--stock-mapping-mode",
        "registry-rule",
        "--base-intelligence-mode",
        "provider-derived",
        "--include-cninfo-announcements",
        "--announcement-start-date",
        "2026-01-01",
        "--include-market-quotes",
        "--output-dir",
        str(tmp_path),
    ]


def test_reviewed_registry_enriched_acceptance_rejects_mock_registry_layer(tmp_path):
    _write_outputs(tmp_path, registry_is_mock=True)

    with pytest.raises(validate_reviewed_registry_enriched_acceptance.AcceptanceError) as exc:
        validate_reviewed_registry_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "registry layer must not be mock" in str(exc.value)


def _write_outputs(output_dir: Path, registry_is_mock: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    registry_layer = _real_layer(
        "narrative_registry",
        "reviewed-registry-store",
        source_url=(
            "reviewed-registry://data/registry/"
            "narrative_registry.reviewed.json#sha256=123456789abc"
        ),
    )
    if registry_is_mock:
        registry_layer = {
            **registry_layer,
            "is_mock": True,
            "source_url": "mock://fixtures/narrative_registry.json",
        }
    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": True,
        "disclosure_message": "数据源为真实 provider，但仍仅用于叙事分析，不构成投资建议。",
        "layers": {
            "holdings": _real_layer("holdings", "eastmoney-fundmobapi"),
            "narrative_registry": registry_layer,
            "stock_mappings": _real_layer(
                "stock_mappings",
                "registry-rule-stock-mapping",
                source_url="derived://registry-term-rule-stock-mapping",
                data_quality="partial",
            ),
            "evidence": _real_layer(
                "evidence",
                "provider-derived-evidence",
                source_url="derived://provider-evidence",
            ),
            "signals": _real_layer(
                "signals",
                "provider-derived-signals",
                source_url="derived://provider-signals",
            ),
            "announcements": _real_layer("announcements", "cninfo-announcement"),
            "market_quotes": _real_layer("market_quotes", "yahoo-chart"),
            "derived_signals": _real_layer(
                "derived_signals",
                "mixed-derived-signals",
                source_url="derived://mixed-derived-signals",
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
        "evidence": [{"evidence_id": "cninfo-600519-0", "source": "cninfo_announcement"}],
    }
    market_quotes = {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "yahoo-chart",
        "data_quality": "fresh",
        "quotes": [{"stock_code": "600519"}],
        "missing_stock_codes": [],
    }
    derived_signal_events = [
        {"signal_id": "SIG_ANN_cninfo-600519-0", "source": "cninfo_announcement"},
        {
            "signal_id": "SIG_QUOTE_600519_premium_baijiu_consumption",
            "source": "market_quote",
        },
    ]
    raw = {
        "metadata": {"fund_code": "161725", "data_quality": "partial"},
        "fund": fund,
        "provider_foundation": provider_foundation,
        "narrative_registry_mode": "reviewed",
        "base_intelligence_mode": "provider-derived",
        "stock_mapping_mode": "registry-rule",
        "stock_narrative_mappings": [
            {"stock_code": "600519", "method": "registry_term_rule"}
        ],
        "announcements": {
            "version": "cninfo-announcement-v1",
            "data_quality": "fresh",
            "announcements": [{"stock_code": "600519"}],
            "missing_stock_codes": [],
        },
        "announcement_evidence": announcement_evidence,
        "market_quotes": market_quotes,
        "evidence": announcement_evidence["evidence"],
        "derived_signal_events": derived_signal_events,
        "signal_events": derived_signal_events,
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": fund,
        "provider_foundation": provider_foundation,
        "narrative_registry_mode": "reviewed",
        "base_intelligence_mode": "provider-derived",
        "stock_mapping_mode": "registry-rule",
        "derived_signal_events": derived_signal_events,
    }
    manifest = {
        "provider_mode": "eastmoney",
        "data_quality": "partial",
        "provider_foundation": provider_foundation,
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    notice = (
        "reviewed-registry-store\nregistry-rule-stock-mapping\n"
        "provider-derived-evidence\nprovider-derived-signals\n"
    )
    (output_dir / "fund_161725_report.md").write_text(notice, encoding="utf-8")
    (output_dir / "fund_161725_report.html").write_text(notice, encoding="utf-8")


def _real_layer(
    layer: str,
    provider_name: str,
    source_url: str | None = None,
    data_quality: str = "fresh",
) -> dict:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": provider_name,
        "provider_version": "real-v1",
        "data_quality": data_quality,
        "source_url": source_url or _source_url(layer),
        "is_mock": False,
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
    }[layer]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
