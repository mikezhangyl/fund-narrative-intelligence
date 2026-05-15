from src.modules.report_writer.writer import render_html_report, render_markdown_report


def test_html_report_renders_structured_sections_without_raw_markdown():
    scoring_payload = {
        "metadata": {
            "fund_code": "000001",
            "as_of_date": "2026-05-13",
            "data_quality": "mock",
            "scoring_model_version": "scoring-v1",
        },
        "fund": {"fund_code": "000001", "fund_name": "Mock Fund"},
        "holdings": [
            {"stock_code": "NVDA", "stock_name": "NVIDIA", "weight": 0.12}
        ],
        "primary_narrative": {
            "narrative_id": "N_AI_INFRA",
            "name": "AI Infrastructure",
            "normalized_exposure": 1.0,
            "state": {
                "stage": "strengthening",
                "sustainability_score": 69.15,
                "confidence": 0.65,
                "data_quality": "mock",
                "dimensions": {
                    "earnings_score": {"score": 85, "confidence": 0.43},
                    "capital_score": {"score": 78, "confidence": 0.39},
                },
            },
        },
        "secondary_narratives": [],
        "mapping_coverage": {
            "coverage_ratio": 1.0,
            "covered_holding_count": 1,
            "total_holding_count": 1,
            "covered_weight": 0.12,
            "total_weight": 0.12,
            "mapping_methods": {"fixture_rule": 1},
        },
        "unmapped_holdings": [],
        "mapping_precision_flags": [
            {
                "type": "multi_match_fallback",
                "severity": "review",
                "stock_code": "NVDA",
                "stock_name": "NVIDIA",
                "industry": "Semiconductors",
                "weight": 0.12,
                "narratives": ["AI Infrastructure", "Semiconductor Capex Cycle"],
                "confidence_before": 0.52,
                "confidence_after": 0.42,
                "recommended_action": "manual_review",
            },
            {
                "type": "broad_industry_fallback",
                "severity": "watch",
                "stock_code": "NVDA",
                "stock_name": "NVIDIA",
                "industry": "Semiconductors",
                "weight": 0.12,
                "narratives": ["AI Infrastructure"],
                "confidence_before": 0.52,
                "confidence_after": 0.48,
                "recommended_action": "curation_review",
            }
        ],
        "mapping_rationales": [
            {
                "stock_code": "NVDA",
                "stock_name": "NVIDIA",
                "industry": "Semiconductors",
                "narrative_id": "N_AI_INFRA",
                "narrative_name": "AI Infrastructure",
                "method": "fixture_rule",
                "confidence": 0.86,
                "mapping_weight": 0.9,
                "matched_terms": [],
                "needs_review": False,
                "precision_flag": None,
                "reason": (
                    "Explicit fixture_rule mapping from the stock-narrative "
                    "mapping fixture."
                ),
            }
        ],
        "excluded_mapping_candidates": [
            {
                "type": "excluded_mapping_candidate",
                "exclusion_id": "EX_SEMI_688036",
                "stock_code": "688036",
                "stock_name": "传音控股",
                "industry": "电子",
                "weight": 0.06,
                "narrative_id": "N_SEMI_CAPEX",
                "narrative_name": "Semiconductor Capex Cycle",
                "method": "registry_term_rule",
                "matched_terms": ["电子"],
                "reason": "Consumer electronics device exposure is too broad.",
                "recommended_action": "candidate_narrative_review",
            }
        ],
        "candidate_narratives": [
            {
                "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
                "name": "Consumer Electronics Globalization",
                "canonical_taxonomy": "Technology Hardware",
                "status": "candidate",
                "source": "mapping_exclusion_review",
                "triggering_stock_codes": ["688036"],
                "related_exclusion_ids": ["EX_SEMI_688036"],
                "aliases": ["consumer electronics exports"],
                "related_terms": ["消费电子"],
                "rationale": "Device exposure candidate, not semiconductor capex.",
                "human_review_status": "candidate",
                "reviewed_by": None,
                "reviewed_at": None,
                "first_seen_at": "2026-05-14",
                "last_updated_at": "2026-05-14",
            }
        ],
        "supporting_evidence": [
            {
                "title": "Guidance raised",
                "source": "mock",
                "event_date": "2026-05-13",
                "summary": "Management raised guidance.",
            }
        ],
        "risk_evidence": [],
        "financial_metrics": {
            "provider_name": "eastmoney-financial-metrics",
            "metrics": [
                {
                    "stock_code": "NVDA",
                    "stock_name": "NVIDIA",
                    "report_date": "2026-03-31",
                    "report_type": "一季报",
                    "revenue_yoy": 18.0,
                    "parent_net_profit_yoy": 22.0,
                    "source_provider": "eastmoney-financial-metrics",
                    "source_url": "https://datacenter.eastmoney.com/securities/api/data/get",
                }
            ],
        },
        "valuation_snapshots": {
            "provider_name": "eastmoney-valuation",
            "valuation_basis": "provider_valuation_metrics",
            "valuations": [
                {
                    "stock_code": "NVDA",
                    "stock_name": "NVIDIA",
                    "latest_price": 106.0,
                    "price_change_percent": 6.0,
                    "pe_ttm": 54.2,
                    "pb": 18.0,
                    "valuation_pressure": "elevated",
                    "source_provider": "eastmoney-valuation",
                    "source_url": "https://push2.eastmoney.com/api/qt/stock/get",
                }
            ],
        },
        "market_quotes": {
            "provider_name": "eastmoney-market-quote",
            "quotes": [
                {
                    "stock_code": "NVDA",
                    "stock_name": "NVIDIA",
                    "latest_price": 1000.0,
                    "change_percent": 1.5,
                    "change_amount": 14.7,
                    "previous_close": 985.3,
                    "volume": 100,
                    "source_provider": "eastmoney-market-quote",
                    "source_url": "https://push2.eastmoney.com/api/qt/ulist.np/get",
                }
            ],
        },
        "news_evidence": {
            "provider_name": "google-news-rss",
            "query_scope": {
                "requested_narrative_ids": ["N_AI_INFRA"],
                "queried_narrative_ids": ["N_AI_INFRA"],
                "omitted_narrative_ids": [],
                "query_limit": 4,
            },
            "evidence": [
                {
                    "evidence_id": "EV_NEWS_N_AI_INFRA_TEST",
                    "narrative_id": "N_AI_INFRA",
                    "title": "AI infrastructure growth accelerates",
                    "summary": "RSS title/snippet matched the narrative.",
                    "sentiment": "positive",
                    "confidence": 0.52,
                    "event_date": "2026-05-14",
                    "source_provider": "google-news-rss",
                    "source_url": "https://example.com/news/ai",
                    "classification_reason": "keyword heuristic over RSS title/snippet",
                }
            ],
        },
        "announcements": {
            "provider_name": "cninfo-announcement",
            "announcements": [
                {
                    "stock_code": "NVDA",
                    "stock_name": "NVIDIA",
                    "title": "2026年度业绩预增公告",
                    "category": "业绩预告",
                    "announcement_date": "2026-05-12",
                    "source_provider": "cninfo-announcement",
                    "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
                }
            ],
        },
        "announcement_evidence": {
            "provider_name": "cninfo-announcement",
            "evidence": [
                {
                    "evidence_id": "EV_ANN_NVDA_N_AI_INFRA",
                    "narrative_id": "N_AI_INFRA",
                    "type": "earnings",
                    "title": "2026年度业绩预增公告",
                    "summary": "Classified CNINFO metadata only. PDF content has not been parsed.",
                    "confidence": 0.64,
                    "event_date": "2026-05-12",
                    "source_provider": "cninfo-announcement",
                    "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
                }
            ],
        },
        "provider_foundation": {
            "effective_data_quality": "mock",
            "disclosure_required": True,
            "disclosure_message": "Mock 数据：本报告使用 V1 Mock fixtures，不代表完整真实环境输出。",
            "layers": {
                "holdings": {
                    "layer": "holdings",
                    "provider_name": "mock-fixture-provider",
                    "provider_version": "mock-v1",
                    "data_quality": "mock",
                    "source_url": None,
                    "is_mock": True,
                    "note": "V1 mock fixture.",
                }
            },
            "degradation_events": [],
        },
    }

    markdown = render_markdown_report(scoring_payload)
    html = render_html_report(scoring_payload)

    assert "<h1>Mock Fund (000001)</h1>" in html
    assert '<section class="holdings">' in html
    assert "<table>" in html
    assert "<th>Stock</th>" in html
    assert '<section class="primary-narrative">' in html
    assert '<section class="mapping-coverage">' in html
    assert '<section class="mapping-precision-flags">' in html
    assert '<section class="mapping-rationales">' in html
    assert '<section class="excluded-mapping-candidates">' in html
    assert '<section class="candidate-narratives">' in html
    assert '<section class="financial-metrics">' in html
    assert '<section class="valuation-snapshots">' in html
    assert '<section class="market-quotes">' in html
    assert '<section class="news-evidence">' in html
    assert '<section class="announcements">' in html
    assert '<section class="announcement-evidence">' in html
    assert '<section class="data-source-notice">' in html
    assert "Mapping Coverage" in html
    assert "Mapping Precision Flags" in html
    assert "Mapping Rationales" in html
    assert "Excluded Mapping Candidates" in html
    assert "Candidate Narratives For Review" in html
    assert "Consumer Electronics Globalization" in html
    assert "candidate_narrative_review" in html
    assert "传音控股" in html
    assert "Explicit fixture_rule mapping" in html
    assert "needs review" in html
    assert "curation review" in html
    assert "Mock 数据" in html
    assert "Financial Metrics" in markdown
    assert "Valuation Snapshots" in markdown
    assert "Market Quotes" in markdown
    assert "News Evidence" in markdown
    assert "Announcement Evidence" in markdown
    assert "eastmoney-financial-metrics" in markdown
    assert "eastmoney-valuation" in markdown
    assert "eastmoney-market-quote" in markdown
    assert "google-news-rss" in markdown
    assert "cninfo-announcement" in markdown
    assert "https://datacenter.eastmoney.com/securities/api/data/get" in html
    assert "https://push2.eastmoney.com/api/qt/stock/get" in html
    assert "https://push2.eastmoney.com/api/qt/ulist.np/get" in html
    assert "https://example.com/news/ai" in html
    assert "https://static.cninfo.com.cn/finalpage/1.PDF" in html
    assert "<h3>AI Infrastructure</h3>" in html
    assert "Lifecycle stage" in html
    assert "### AI Infrastructure" not in html
    assert "| Stock |" not in html
    assert "不构成投资建议" in html
