import json
from pathlib import Path

import pytest
from scripts import validate_reviewed_mapping_enriched_acceptance


def test_reviewed_mapping_enriched_acceptance_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    snapshot_path = tmp_path / "fund_161725_workspace_snapshot.json"
    registry_path.write_text(_reviewed_registry_text(), encoding="utf-8")
    mappings_path.write_text(_reviewed_mapping_text(), encoding="utf-8")
    snapshot_path.write_text('{"version": "old-workspace-snapshot"}', encoding="utf-8")

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_outputs(tmp_path)
        if args == ["--validate-artifact-contracts", str(tmp_path)]:
            assert not snapshot_path.exists()
        if args == ["--build-workspace-snapshot", str(tmp_path)]:
            assert not snapshot_path.exists()
            snapshot_path.write_text('{"version": "workspace-snapshot-v1"}', encoding="utf-8")
        if args == ["--validate-workspace-snapshot", str(snapshot_path)]:
            assert snapshot_path.exists()
        return 0

    monkeypatch.setattr(
        validate_reviewed_mapping_enriched_acceptance.pipeline_main,
        "main",
        fake_main,
    )

    exit_code = validate_reviewed_mapping_enriched_acceptance.main(
        [
            "--narrative-registry-path",
            str(registry_path),
            "--stock-mappings-path",
            str(mappings_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Reviewed-mapping enriched acceptance passed:" in captured.out
    assert "valuation=eastmoney" in captured.out
    assert "workspace_snapshot=fund_161725_workspace_snapshot.json" in captured.out
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
        "reviewed",
        "--stock-mappings-path",
        str(mappings_path),
        "--base-intelligence-mode",
        "provider-derived",
        "--include-cninfo-announcements",
        "--announcement-start-date",
        "2026-01-01",
        "--include-market-quotes",
        "--include-valuation-snapshots",
        "--valuation-source",
        "eastmoney",
        "--include-news-evidence",
        "--output-dir",
        str(tmp_path),
    ]
    assert calls[1] == ["--validate-artifact-contracts", str(tmp_path)]
    assert calls[2] == ["--build-workspace-snapshot", str(tmp_path)]
    assert calls[3] == [
        "--validate-workspace-snapshot",
        str(snapshot_path),
    ]


def test_reviewed_mapping_enriched_acceptance_rejects_registry_rule_mapping(tmp_path):
    _write_outputs(tmp_path, mapping_method="registry_term_rule")

    with pytest.raises(validate_reviewed_mapping_enriched_acceptance.AcceptanceError) as exc:
        validate_reviewed_mapping_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "all selected mappings must use reviewed_mapping" in str(exc.value)


def test_reviewed_mapping_enriched_acceptance_rejects_missing_valuation(tmp_path):
    _write_outputs(tmp_path, include_valuation=False)

    with pytest.raises(validate_reviewed_mapping_enriched_acceptance.AcceptanceError) as exc:
        validate_reviewed_mapping_enriched_acceptance.validate_acceptance_outputs(tmp_path)

    assert "valuation_snapshots is required" in str(exc.value)


def _write_outputs(
    output_dir: Path,
    mapping_method: str = "reviewed_mapping",
    include_valuation: bool = True,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": True,
        "disclosure_message": "数据源为真实 provider，但仍仅用于叙事分析，不构成投资建议。",
        "layers": {
            "holdings": _real_layer("holdings", "eastmoney-fundmobapi"),
            "narrative_registry": _real_layer(
                "narrative_registry",
                "reviewed-registry-store",
                source_url=(
                    "reviewed-registry://data/registry/"
                    "narrative_registry.reviewed.json#sha256=123456789abc"
                ),
                review_metadata=_review_metadata(),
            ),
            "stock_mappings": _real_layer(
                "stock_mappings",
                "reviewed-mapping-store",
                source_url=(
                    "reviewed-mapping://data/registry/"
                    "stock_narrative_mappings.reviewed.json#sha256=123456789abc"
                ),
                data_quality="partial",
                review_metadata=_review_metadata(),
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
            **(
                {"valuation": _real_layer("valuation", "eastmoney-valuation")}
                if include_valuation
                else {}
            ),
            "news_evidence": _real_layer("news_evidence", "google-news-rss"),
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
    valuation_snapshots = {
        "version": "valuation-snapshot-v1",
        "provider_name": "eastmoney-valuation",
        "provider_version": "eastmoney-valuation-v1",
        "data_quality": "fresh",
        "source_url": "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "valuation_basis": "provider_valuation_metrics",
        "valuations": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "source": "provider_valuation_metrics",
                "source_provider": "eastmoney-valuation",
                "source_url": "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519",
                "latest_price": 1600.0,
                "change_percent": 3.4,
                "valuation_pressure": "elevated",
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "pe_ttm": 42.0,
                "pb": 8.2,
                "market_cap": 1680759514466.55,
                "float_market_cap": 1680759514466.55,
                "turnover_rate": 0.44,
            }
        ],
        "missing_stock_codes": [],
    }
    news_evidence = {
        "version": "news-evidence-v1",
        "provider_name": "google-news-rss",
        "provider_version": "google-news-rss-v1",
        "data_quality": "fresh",
        "source_url": "https://news.google.com/rss/search",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "query_scope": {
            "requested_narrative_ids": ["premium_baijiu_consumption"],
            "queried_narrative_ids": ["premium_baijiu_consumption"],
            "omitted_narrative_ids": [],
            "query_limit": 4,
        },
        "evidence": [
            {
                "evidence_id": "news-premium-baijiu-0",
                "narrative_id": "premium_baijiu_consumption",
                "type": "news",
                "source": "google_news_rss",
                "source_url": "https://example.com/news",
            }
        ],
        "missing_narrative_ids": [],
        "skipped_item_count": 0,
        "degradation_events": [],
    }
    derived_signal_events = [
        {"signal_id": "SIG_ANN_cninfo-600519-0", "source": "cninfo_announcement"},
        {"signal_id": "SIG_NEWS_news-premium-baijiu-0", "source": "news_evidence"},
        {
            "signal_id": "SIG_QUOTE_600519_premium_baijiu_consumption",
            "source": "market_quote",
        },
        {
            "signal_id": "SIG_VAL_600519_premium_baijiu_consumption_VALUATION_EXTREME",
            "source": "valuation_snapshot",
            "source_provider": "eastmoney-valuation",
            "signal_type": "valuation_extreme",
        },
    ]
    raw = {
        "metadata": {"fund_code": "161725", "data_quality": "partial"},
        "fund": fund,
        "provider_foundation": provider_foundation,
        "narrative_registry_mode": "reviewed",
        "base_intelligence_mode": "provider-derived",
        "stock_mapping_mode": "reviewed",
        "stock_narrative_mappings": [{"stock_code": "600519", "method": mapping_method}],
        "mapping_coverage": {"mapping_methods": {mapping_method: 1}},
        "announcements": {
            "version": "cninfo-announcement-v1",
            "data_quality": "fresh",
            "announcements": [{"stock_code": "600519"}],
            "missing_stock_codes": [],
        },
        "announcement_evidence": announcement_evidence,
        "news_evidence": news_evidence,
        "market_quotes": market_quotes,
        **({"valuation_snapshots": valuation_snapshots} if include_valuation else {}),
        "evidence": [*announcement_evidence["evidence"], *news_evidence["evidence"]],
        "derived_signal_events": derived_signal_events,
        "signal_events": derived_signal_events,
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": fund,
        "provider_foundation": provider_foundation,
        "narrative_registry_mode": "reviewed",
        "base_intelligence_mode": "provider-derived",
        "stock_mapping_mode": "reviewed",
        "news_evidence": news_evidence,
        **({"valuation_snapshots": valuation_snapshots} if include_valuation else {}),
        "derived_signal_events": derived_signal_events,
    }
    manifest = {
        "provider_mode": "eastmoney",
        "data_quality": "partial",
        "provider_foundation": provider_foundation,
    }
    source_table = {
        "version": "source-table-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_foundation": provider_foundation,
        "layers": list(provider_foundation["layers"].values()),
        "degradation_events": provider_foundation["degradation_events"],
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_source_table.json", source_table)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    notice = (
        "reviewed-registry-store\nreviewed-mapping-store\n"
        "provider-derived-evidence\nprovider-derived-signals\n"
        "eastmoney-valuation\n"
    )
    (output_dir / "fund_161725_report.md").write_text(notice, encoding="utf-8")
    (output_dir / "fund_161725_report.html").write_text(notice, encoding="utf-8")


def _real_layer(
    layer: str,
    provider_name: str,
    source_url: str | None = None,
    data_quality: str = "fresh",
    review_metadata: dict | None = None,
) -> dict:
    payload = {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": provider_name,
        "provider_version": "real-v1",
        "data_quality": data_quality,
        "source_url": source_url or _source_url(layer),
        "is_mock": False,
        "note": "",
    }
    if review_metadata is not None:
        payload["review_metadata"] = review_metadata
    return payload


def _source_url(layer: str) -> str:
    return {
        "holdings": "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition?FCODE=161725",
        "announcements": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
        "market_quotes": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
        "valuation": "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519",
        "news_evidence": "https://news.google.com/rss/search",
    }[layer]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _reviewed_registry_text() -> str:
    payload = {
        "review_metadata": _review_metadata(),
        "narratives": [
            {
                "narrative_id": "N_BAIJIU_CONSUMPTION",
                "human_review_status": "approved",
                "reviewed_by": "seed-curation",
                "reviewed_at": "2026-05-15",
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _reviewed_mapping_text() -> str:
    payload = {
        "review_metadata": _review_metadata(),
        "mappings": [
            {
                "stock_code": "600519",
                "narrative_id": "N_BAIJIU_CONSUMPTION",
                "method": "reviewed_mapping",
                "review": _review_entry(),
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _review_metadata() -> dict:
    return {
        "review_schema_version": "review-metadata-v1",
        "reviewed_by": "seed-curation",
        "reviewed_at": "2026-05-15",
        "review_note": "Test reviewed store metadata.",
    }


def _review_entry() -> dict:
    return {
        "status": "approved",
        "reviewed_by": "seed-curation",
        "reviewed_at": "2026-05-15",
        "review_note": "Test reviewed mapping metadata.",
    }
