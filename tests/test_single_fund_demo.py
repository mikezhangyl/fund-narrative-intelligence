import json

from scripts.run_single_fund_demo import main as run_demo_main
from src.modules.single_fund_demo import (
    SingleFundDemoError,
    build_single_fund_demo_payload,
    render_single_fund_demo_html,
    validate_single_fund_demo_payload,
)


def test_build_single_fund_demo_payload_for_web_ready_fund_view():
    payload = build_single_fund_demo_payload(
        raw=_raw_payload(),
        scoring=_scoring_payload(),
        workspace_snapshot=_workspace_snapshot(),
    )

    validate_single_fund_demo_payload(payload)
    assert payload["version"] == "single-fund-demo-v1"
    assert payload["web_ready"] is True
    assert payload["primary_narrative"]["name"] == "Premium Baijiu Consumption"
    assert payload["holdings"][0]["stock_code"] == "600519"
    assert payload["holdings"][0]["narrative_name"] == "Premium Baijiu Consumption"
    assert payload["data_status"]["mock_layer_count"] == 0


def test_validate_single_fund_demo_rejects_real_demo_with_mock_layer():
    payload = build_single_fund_demo_payload(
        raw=_raw_payload(),
        scoring=_scoring_payload(mock_layer=True),
        workspace_snapshot=_workspace_snapshot(mock_layer=True),
    )

    try:
        validate_single_fund_demo_payload(payload)
    except SingleFundDemoError as exc:
        assert "mock provider layers" in str(exc)
    else:
        raise AssertionError("expected mock layer validation failure")


def test_render_single_fund_demo_html_defaults_to_chinese_with_english_toggle():
    payload = build_single_fund_demo_payload(
        raw=_raw_payload(),
        scoring=_scoring_payload(),
        workspace_snapshot=_workspace_snapshot(),
    )

    html = render_single_fund_demo_html(payload)

    assert '<html lang="zh-CN">' in html
    assert 'data-lang="en"' in html
    assert "十大重仓叙事映射" in html
    assert "Top Holdings Narrative Map" in html
    assert "高端白酒消费" in html
    assert "Premium Baijiu Consumption" in html
    assert "走弱" in html
    assert "weakening" in html
    assert "本次使用真实数据源" in html


def test_run_single_fund_demo_script_writes_demo_artifacts(tmp_path, monkeypatch):
    from scripts import run_single_fund_demo

    def fake_run_pipeline(**kwargs):
        output_dir = kwargs["output_dir"]
        raw_path = output_dir / "fund_161725_raw.json"
        scoring_path = output_dir / "fund_161725_scoring.json"
        raw_path.write_text(json.dumps(_raw_payload()), encoding="utf-8")
        scoring_path.write_text(json.dumps(_scoring_payload()), encoding="utf-8")
        return {"raw": raw_path, "scoring": scoring_path}

    def fake_build_workspace_snapshot(output_dir):
        path = output_dir / "fund_161725_workspace_snapshot.json"
        path.write_text(json.dumps(_workspace_snapshot()), encoding="utf-8")
        return path

    monkeypatch.setattr(run_single_fund_demo, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        run_single_fund_demo,
        "build_workspace_snapshot",
        fake_build_workspace_snapshot,
    )

    result = run_demo_main(["--output-dir", str(tmp_path)])

    assert result == 0
    assert (tmp_path / "fund_161725_demo.json").exists()
    html = (tmp_path / "fund_161725_demo.html").read_text(encoding="utf-8")
    assert "十大重仓叙事映射" in html
    assert "Top Holdings Narrative Map" in html


def _raw_payload():
    holdings = [
        {
            "stock_code": code,
            "stock_name": name,
            "industry": "食品饮料",
            "weight": weight,
        }
        for code, name, weight in [
            ("600519", "贵州茅台", 0.1833),
            ("000858", "五粮液", 0.1614),
            ("000568", "泸州老窖", 0.1470),
            ("600809", "山西汾酒", 0.1432),
            ("002304", "洋河股份", 0.0774),
            ("000596", "古井贡酒", 0.0451),
            ("603369", "今世缘", 0.0407),
            ("603198", "迎驾贡酒", 0.0228),
            ("600702", "舍得酒业", 0.0185),
            ("603589", "口子窖", 0.0182),
        ]
    ]
    mappings = [
        {
            "stock_code": item["stock_code"],
            "narrative_id": "N_BAIJIU_CONSUMPTION",
            "confidence": 0.84,
            "mapping_weight": 0.9,
            "method": "reviewed_mapping",
        }
        for item in holdings
    ]
    return {
        "fund": {
            "fund_code": "161725",
            "fund_name": "Eastmoney Fund 161725",
            "fund_type": "fund",
            "currency": "CNY",
        },
        "as_of_date": "2026-03-31",
        "holdings": holdings,
        "narrative_registry": [
            {
                "narrative_id": "N_BAIJIU_CONSUMPTION",
                "name": "Premium Baijiu Consumption",
            }
        ],
        "stock_narrative_mappings": mappings,
        "mapping_coverage": {"covered_weight": 0.8576, "coverage_ratio": 1.0},
        "announcement_evidence": {
            "evidence": [
                {
                    "event_date": "2026-01-09",
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                    "title": "Board announcement",
                    "source": "cninfo_announcement",
                    "source_url": "https://example.test/announcement.pdf",
                    "sentiment": "mixed",
                }
            ]
        },
        "news_evidence": {
            "evidence": [
                {
                    "event_date": "2026-04-21",
                    "title": "Premium spirits report",
                    "source_provider": "google-news-rss",
                    "source_url": "https://example.test/news",
                    "sentiment": "positive",
                }
            ]
        },
        "derived_signal_events": [
            {
                "event_date": "2026-05-15",
                "source_stock_code": "600519",
                "signal_type": "valuation_pressure",
                "strength": 0.5,
                "confidence": 0.4,
                "source_provider": "eastmoney-valuation",
            }
        ],
        "valuation_snapshots": {
            "valuations": [
                {
                    "stock_code": "600519",
                    "latest_price": 1331.96,
                    "price_change_percent": -0.76,
                    "pe_ttm": 15.31,
                    "source_url": "https://example.test/valuation",
                }
            ]
        },
        "financial_metrics": {
            "metrics": [
                {
                    "stock_code": "600519",
                    "revenue_yoy": 6.33,
                    "parent_net_profit_yoy": 1.47,
                    "report_date": "2026-03-31",
                    "source_url": "https://example.test/financial",
                }
            ]
        },
    }


def _scoring_payload(mock_layer=False):
    return {
        "primary_narrative": {
            "narrative_id": "N_BAIJIU_CONSUMPTION",
            "name": "Premium Baijiu Consumption",
            "confidence": 0.8166,
            "normalized_exposure": 1.0,
            "raw_exposure": 0.761837,
            "interpretation": {"stage_explanation": "This narrative is weakening."},
            "state": {
                "stage": "weakening",
                "sustainability_score": 44.5,
                "dimensions": {
                    "earnings_score": {
                        "score": 43,
                        "supporting_signal_count": 3,
                        "risk_signal_count": 7,
                        "confidence": 0.3492,
                    }
                },
            },
        },
        "provider_foundation": _provider_foundation(mock_layer=mock_layer),
    }


def _workspace_snapshot(mock_layer=False):
    return {
        "as_of_date": "2026-03-31",
        "provider_foundation": _provider_foundation(mock_layer=mock_layer),
        "data_source_notice": {
            "mock_layer_count": 1 if mock_layer else 0,
            "unavailable_layer_count": 0,
        },
    }


def _provider_foundation(mock_layer=False):
    return {
        "effective_data_quality": "mock" if mock_layer else "fresh",
        "disclosure_required": mock_layer,
        "disclosure_message": "Mock data is present" if mock_layer else "",
        "degradation_events": [
            {
                "type": "provider_fallback",
                "provider": "eastmoney-market-quote",
                "fallback_provider": "yahoo-chart",
            }
        ],
        "layers": {
            "holdings": {
                "layer": "holdings",
                "display_name": "Fund holdings",
                "provider_name": "mock-fixture-provider"
                if mock_layer
                else "eastmoney-fundmobapi",
                "data_quality": "mock" if mock_layer else "fresh",
                "source_url": "mock://fixture"
                if mock_layer
                else "https://example.test/holdings",
                "is_mock": mock_layer,
            }
        },
    }
