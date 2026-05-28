import json
from pathlib import Path


def write_provider_routing_outputs(
    output_dir: Path,
    market_provider: str = "yahoo-chart",
    valuation_provider: str = "eastmoney-valuation",
    financial_provider: str = "eastmoney-financial-metrics",
    layer_fallbacks: dict[str, dict[str, str]] | None = None,
    provider_unavailable: dict[str, str] | None = None,
    omit_layer_fallback: set[str] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    omit_layer_fallback = omit_layer_fallback or set()
    if layer_fallbacks is None:
        layer_fallbacks = {
            "market_quotes": {"provider": "akshare", "fallback_provider": "eastmoney"},
            "valuation_snapshots": {
                "provider": "tushare",
                "fallback_provider": "eastmoney",
            },
            "financial_metrics": {
                "provider": "tushare",
                "fallback_provider": "eastmoney",
            },
        }
    if provider_unavailable is None:
        provider_unavailable = {
            "akshare-market-quote": "akshare unavailable",
            "tushare-valuation": "TUSHARE_TOKEN is not configured",
            "tushare-financial-metrics": "TUSHARE_TOKEN is not configured",
        }

    degradation_events = [
        *[
            {
                "type": "provider_unavailable",
                "provider": provider_name,
                "reason": reason,
            }
            for provider_name, reason in provider_unavailable.items()
        ],
        {
            "type": "provider_fallback",
            "provider": "eastmoney-market-quote",
            "fallback_provider": "yahoo-chart",
            "reason": "Eastmoney quote fetch failed for 600519: timeout",
        },
    ]
    for layer, payload in layer_fallbacks.items():
        if layer in omit_layer_fallback:
            continue
        degradation_events.append(
            {
                "type": "provider_fallback",
                "layer": layer,
                "provider": payload["provider"],
                "fallback_provider": payload["fallback_provider"],
                "reason": "Primary provider returned unavailable payload",
            }
        )

    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": True,
        "disclosure_message": (
            "Provider routing fallback active: AKShare/Tushare primary paths "
            "degraded to Eastmoney/Yahoo while base evidence layers remain mixed."
        ),
        "layers": {
            "holdings": _real_layer(
                "holdings",
                "eastmoney-fundmobapi",
                "eastmoney-v1",
                "fresh",
                "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition?FCODE=161725",
            ),
            "narrative_registry": _mock_layer("narrative_registry"),
            "stock_mappings": _mock_layer("stock_mappings"),
            "evidence": _mock_layer("evidence"),
            "signals": _mock_layer("signals"),
            "market_quotes": _real_layer(
                "market_quotes",
                market_provider,
                "market-v1",
                "fresh",
                _market_source_url(market_provider),
            ),
            "valuation": _real_layer(
                "valuation",
                valuation_provider,
                "valuation-v1",
                "fresh",
                _valuation_source_url(valuation_provider),
            ),
            "financial_metrics": _real_layer(
                "financial_metrics",
                financial_provider,
                "financial-v1",
                "fresh",
                _financial_source_url(financial_provider),
            ),
            "derived_signals": _real_layer(
                "derived_signals",
                "mixed-derived-signals",
                "derived-signals-v1",
                "fresh",
                "derived://mixed-derived-signals",
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
        "provider_name": market_provider,
        "provider_version": "market-provider-v1",
        "data_quality": "fresh",
        "source_url": _market_source_url(market_provider),
        "retrieved_at": "2026-05-15T00:00:00+00:00",
        "quotes": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "source_provider": market_provider,
                "source_url": _market_source_url(market_provider),
                "latest_price": 1560.0,
                "change_percent": 1.96,
                "change_amount": 30.0,
                "volume": 123456.0,
                "amount": 987654321.0,
                "high": 1568.0,
                "low": 1544.0,
                "open": 1550.0,
                "previous_close": 1530.0,
                "retrieved_at": "2026-05-15T00:00:00+00:00",
            }
        ],
        "missing_stock_codes": [],
    }
    valuation_snapshots = {
        "version": "valuation-snapshot-v1",
        "provider_name": valuation_provider,
        "provider_version": "valuation-provider-v1",
        "data_quality": "fresh",
        "source_url": _valuation_source_url(valuation_provider),
        "retrieved_at": "2026-05-15T00:00:00+00:00",
        "valuation_basis": "provider_valuation_metrics",
        "valuations": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "latest_price": 1560.0,
                "previous_close": 1530.0,
                "price_change_percent": 1.96,
                "valuation_pressure": "elevated",
                "source": "provider_valuation_metrics",
                "source_provider": valuation_provider,
                "source_url": _valuation_source_url(valuation_provider),
                "retrieved_at": "2026-05-15T00:00:00+00:00",
                "pe_ttm": 24.6,
                "pb": 8.3,
                "market_cap": 1970000000.0,
                "float_market_cap": 1965000000.0,
                "turnover_rate": 0.42,
            }
        ],
        "missing_stock_codes": [],
    }
    financial_metrics = {
        "version": "financial-metrics-v1",
        "provider_name": financial_provider,
        "provider_version": "financial-provider-v1",
        "data_quality": "fresh",
        "source_url": _financial_source_url(financial_provider),
        "retrieved_at": "2026-05-15T00:00:00+00:00",
        "metrics": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report_date": "2025-03-31",
                "report_type": "一季报",
                "notice_date": "2025-04-29",
                "currency": "CNY",
                "revenue": 51400000000.0,
                "revenue_yoy": 6.33,
                "parent_net_profit": 24800000000.0,
                "parent_net_profit_yoy": 1.47,
                "deduct_parent_net_profit_yoy": 1.45,
                "roe": 10.57,
                "gross_margin": 91.23,
                "debt_asset_ratio": 12.12,
                "source": "provider_financial_metrics",
                "source_provider": financial_provider,
                "source_url": _financial_source_url(financial_provider),
                "retrieved_at": "2026-05-15T00:00:00+00:00",
            }
        ],
        "missing_stock_codes": [],
    }
    derived_signal_events = [
        {
            "signal_id": "SIG_QUOTE_600519_PREMIUM_BAIJIU",
            "narrative_id": "premium_baijiu_consumption",
            "signal_type": "relative_strength_up",
            "strength": 0.4,
            "confidence": 0.44,
            "confidence_multiplier": 0.65,
            "event_date": "2026-05-15",
            "half_life_days": 10,
            "source": "market_quote",
            "source_provider": market_provider,
            "source_stock_code": "600519",
            "source_url": _market_source_url(market_provider),
            "derivation_reason": "positive market quote change percent",
        },
        {
            "signal_id": "SIG_VAL_600519_PREMIUM_BAIJIU",
            "narrative_id": "premium_baijiu_consumption",
            "signal_type": "valuation_extreme",
            "strength": 1.0,
            "confidence": 0.645,
            "confidence_multiplier": 0.75,
            "event_date": "2026-05-15",
            "half_life_days": 30,
            "source": "valuation_snapshot",
            "source_provider": valuation_provider,
            "source_stock_code": "600519",
            "source_url": _valuation_source_url(valuation_provider),
            "derivation_reason": "elevated provider valuation metrics",
        },
        {
            "signal_id": "SIG_FIN_600519_PREMIUM_BAIJIU",
            "narrative_id": "premium_baijiu_consumption",
            "signal_type": "revenue_growth_up",
            "strength": 0.7,
            "confidence": 0.7,
            "confidence_multiplier": 0.75,
            "event_date": "2025-04-29",
            "half_life_days": 45,
            "source": "financial_metrics",
            "source_provider": financial_provider,
            "source_stock_code": "600519",
            "source_url": _financial_source_url(financial_provider),
            "derivation_reason": "positive provider financial metrics",
        },
    ]
    raw = {
        "metadata": {
            "fund_code": "161725",
            "as_of_date": "2026-03-31",
            "data_quality": "partial",
        },
        "fund": fund,
        "provider_foundation": provider_foundation,
        "market_quotes": market_quotes,
        "valuation_snapshots": valuation_snapshots,
        "financial_metrics": financial_metrics,
        "signal_events": derived_signal_events,
        "derived_signal_events": derived_signal_events,
        "degradation_events": degradation_events,
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": fund,
        "provider_foundation": provider_foundation,
        "market_quotes": market_quotes,
        "valuation_snapshots": valuation_snapshots,
        "financial_metrics": financial_metrics,
        "derived_signal_events": derived_signal_events,
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {
                "total_count": 0,
                "pending_count": 0,
                "action_required": False,
            },
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
    source_table = {
        "version": "source-table-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_foundation": provider_foundation,
        "layers": list(provider_foundation["layers"].values()),
        "degradation_events": degradation_events,
    }
    signal_trace = {
        "version": "signal-trace-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_foundation": provider_foundation,
        "signal_count": len(derived_signal_events),
        "narratives": [],
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
            "review_queue": {
                "path": "fund_161725_review_queue.json",
                "format": "json",
            },
            "source_table": {
                "path": "fund_161725_source_table.json",
                "format": "json",
            },
            "signal_trace": {
                "path": "fund_161725_signal_trace.json",
                "format": "json",
            },
            "markdown": {"path": "fund_161725_report.md", "format": "markdown"},
            "html": {"path": "fund_161725_report.html", "format": "html"},
        },
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_review_queue.json", review_queue)
    _write_json(output_dir / "fund_161725_source_table.json", source_table)
    _write_json(output_dir / "fund_161725_signal_trace.json", signal_trace)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    notice = (
        "Data Source Notice\nProvider routing fallback active\nEastmoney\n"
        "Tushare\nAKShare\nYahoo\nMock fixtures\n"
    )
    (output_dir / "fund_161725_report.md").write_text(notice, encoding="utf-8")
    (output_dir / "fund_161725_report.html").write_text(notice, encoding="utf-8")


def _real_layer(
    layer: str,
    provider_name: str,
    provider_version: str,
    data_quality: str,
    source_url: str,
) -> dict:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": provider_name,
        "provider_version": provider_version,
        "data_quality": data_quality,
        "source_url": source_url,
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


def _market_source_url(provider_name: str) -> str:
    urls = {
        "akshare-market-quote": "https://akshare.akfamily.xyz/data/stock/stock.html",
        "eastmoney-market-quote": "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "yahoo-chart": "https://query1.finance.yahoo.com/v8/finance/chart/600519.SS",
        "mixed-market-quote": "multiple://market-quotes",
    }
    return urls[provider_name]


def _valuation_source_url(provider_name: str) -> str:
    return {
        "tushare-valuation": "https://api.tushare.pro",
        "eastmoney-valuation": "https://push2.eastmoney.com/api/qt/stock/get",
    }[provider_name]


def _financial_source_url(provider_name: str) -> str:
    return {
        "tushare-financial-metrics": "https://api.tushare.pro",
        "eastmoney-financial-metrics": "https://datacenter.eastmoney.com/securities/api/data/get",
    }[provider_name]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
