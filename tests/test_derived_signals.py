from src.modules.signal_service.derived import (
    derive_announcement_signal_events,
    derive_market_quote_signal_events,
    derive_news_signal_events,
)
from src.modules.signal_service.scoring import calculate_dimension_score
from src.validation import validate_signal_payload


def test_derives_earnings_announcement_signal_from_positive_evidence():
    evidence = [
        {
            "evidence_id": "EV_ANN_000001_N_BANK_123",
            "narrative_id": "N_BANK",
            "type": "earnings",
            "source": "cninfo_announcement",
            "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
            "title": "2026年度业绩预增公告",
            "summary": "positive earnings metadata",
            "sentiment": "positive",
            "confidence": 0.552,
            "event_date": "2026-05-12",
            "stock_code": "000001",
            "stock_name": "平安银行",
        }
    ]

    signals = derive_announcement_signal_events(evidence)

    assert signals == [
        {
            "signal_id": "SIG_ANN_EV_ANN_000001_N_BANK_123",
            "narrative_id": "N_BANK",
            "signal_type": "revenue_growth_up",
            "strength": 0.552,
            "confidence": 0.552,
            "confidence_multiplier": 0.85,
            "event_date": "2026-05-12",
            "half_life_days": 45,
            "source": "cninfo_announcement",
            "source_evidence_id": "EV_ANN_000001_N_BANK_123",
            "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
            "derivation_reason": "positive earnings announcement evidence",
        }
    ]
    validate_signal_payload({"version": "signals-v1", "signal_events": signals})


def test_derives_counter_evidence_signal_from_negative_risk_evidence():
    evidence = [
        {
            "evidence_id": "EV_ANN_300750_N_NEW_ENERGY_123",
            "narrative_id": "N_NEW_ENERGY",
            "type": "risk",
            "source": "cninfo_announcement",
            "source_url": "https://static.cninfo.com.cn/finalpage/2.PDF",
            "title": "重大诉讼及风险提示公告",
            "summary": "negative risk metadata",
            "sentiment": "negative",
            "confidence": 0.405,
            "event_date": "2026-05-09",
        }
    ]

    signals = derive_announcement_signal_events(evidence)

    assert signals[0]["signal_type"] == "regulatory_risk"
    assert signals[0]["strength"] == 0.405
    assert signals[0]["confidence_multiplier"] == 0.85


def test_derives_low_weight_momentum_signal_from_mixed_financial_disclosure():
    evidence = [
        {
            "evidence_id": "EV_MIXED",
            "narrative_id": "N_BANK",
            "type": "financial_report",
            "source": "cninfo_announcement",
            "source_url": "https://static.cninfo.com.cn/finalpage/3.PDF",
            "sentiment": "mixed",
            "confidence": 0.3,
            "event_date": "2026-05-12",
        }
    ]

    signals = derive_announcement_signal_events(evidence)

    assert signals[0]["signal_type"] == "management_mentions_up"
    assert signals[0]["strength"] == 0.18
    assert signals[0]["confidence"] == 0.3
    assert signals[0]["confidence_multiplier"] == 0.55


def test_ignores_generic_mixed_or_non_announcement_evidence():
    evidence = [
        {
            "evidence_id": "EV_GENERIC",
            "narrative_id": "N_BANK",
            "type": "announcement",
            "source": "cninfo_announcement",
            "sentiment": "mixed",
            "confidence": 0.3,
            "event_date": "2026-05-12",
        },
        {
            "evidence_id": "EV_NEWS",
            "narrative_id": "N_BANK",
            "type": "earnings",
            "source": "news",
            "sentiment": "positive",
            "confidence": 0.7,
            "event_date": "2026-05-12",
        },
    ]

    assert derive_announcement_signal_events(evidence) == []


def test_derives_positive_momentum_signal_from_news_evidence():
    evidence = [
        {
            "evidence_id": "EV_NEWS_N_AI_INFRA_123",
            "narrative_id": "N_AI_INFRA",
            "type": "news",
            "source": "google_news_rss",
            "source_url": "https://example.com/news/ai",
            "title": "AI infrastructure growth accelerates",
            "summary": "RSS title/snippet only.",
            "sentiment": "positive",
            "confidence": 0.52,
            "event_date": "2026-05-14",
            "source_provider": "google-news-rss",
        }
    ]

    signals = derive_news_signal_events(evidence)

    assert signals == [
        {
            "signal_id": "SIG_NEWS_EV_NEWS_N_AI_INFRA_123",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "news_frequency_up",
            "strength": 0.416,
            "confidence": 0.52,
            "confidence_multiplier": 0.55,
            "event_date": "2026-05-14",
            "half_life_days": 14,
            "source": "news_evidence",
            "source_provider": "google-news-rss",
            "source_evidence_id": "EV_NEWS_N_AI_INFRA_123",
            "source_url": "https://example.com/news/ai",
            "derivation_reason": "provider news evidence",
        }
    ]
    validate_signal_payload({"version": "signals-v1", "signal_events": signals})

    momentum_score = calculate_dimension_score(
        "momentum_score",
        signals,
        as_of_date="2026-05-14",
        data_quality="partial",
    )
    assert momentum_score["supporting_signal_count"] == 1
    assert momentum_score["score"] > 50


def test_derives_language_decay_signal_from_negative_news_evidence():
    evidence = [
        {
            "evidence_id": "EV_NEWS_N_NEW_ENERGY_123",
            "narrative_id": "N_NEW_ENERGY",
            "type": "news",
            "source": "google_news_rss",
            "source_url": "https://example.com/news/risk",
            "title": "Battery demand risk warning",
            "summary": "RSS title/snippet only.",
            "sentiment": "negative",
            "confidence": 0.5,
            "event_date": "2026-05-14",
            "source_provider": "google-news-rss",
        }
    ]

    signals = derive_news_signal_events(evidence)

    assert signals[0]["signal_type"] == "language_decay"
    assert signals[0]["strength"] == 0.35
    momentum_score = calculate_dimension_score(
        "momentum_score",
        signals,
        as_of_date="2026-05-14",
        data_quality="partial",
    )
    assert momentum_score["risk_signal_count"] == 1
    assert momentum_score["score"] < 50


def test_derives_low_weight_research_signal_from_mixed_news_evidence():
    evidence = [
        {
            "evidence_id": "EV_NEWS_N_HEALTHCARE_123",
            "narrative_id": "N_HEALTHCARE",
            "type": "news",
            "source": "google_news_rss",
            "source_url": "https://example.com/news/healthcare",
            "title": "Healthcare innovation coverage continues",
            "summary": "RSS title/snippet only.",
            "sentiment": "mixed",
            "confidence": 0.46,
            "event_date": "2026-05-14",
            "source_provider": "google-news-rss",
        }
    ]

    signals = derive_news_signal_events(evidence)

    assert signals[0]["signal_type"] == "research_mentions_up"
    assert signals[0]["strength"] == 0.23
    assert signals[0]["confidence_multiplier"] == 0.45


def test_derives_relative_strength_signal_from_positive_market_quote():
    market_quotes = {
        "version": "eastmoney-market-quote-v1",
        "data_quality": "fresh",
        "quotes": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "change_percent": 3.2,
                "source_provider": "eastmoney",
                "source_url": "https://push2his.eastmoney.com/quote",
                "retrieved_at": "2026-05-14T12:00:00+00:00",
            }
        ],
    }
    stock_mappings = [
        {
            "stock_code": "600519",
            "narrative_id": "N_BAIJIU",
            "confidence": 0.8,
        }
    ]

    signals = derive_market_quote_signal_events(
        market_quotes_payload=market_quotes,
        stock_mappings=stock_mappings,
        as_of_date="2026-05-14",
    )

    assert signals == [
        {
            "signal_id": "SIG_QUOTE_600519_N_BAIJIU_REL_STRENGTH_UP",
            "narrative_id": "N_BAIJIU",
            "signal_type": "relative_strength_up",
            "strength": 0.64,
            "confidence": 0.44,
            "confidence_multiplier": 0.65,
            "event_date": "2026-05-14",
            "half_life_days": 10,
            "source": "market_quote",
            "source_provider": "eastmoney",
            "source_stock_code": "600519",
            "source_url": "https://push2his.eastmoney.com/quote",
            "derivation_reason": "positive market quote change percent",
        }
    ]
    validate_signal_payload({"version": "signals-v1", "signal_events": signals})


def test_derives_relative_weakness_signal_from_negative_market_quote():
    market_quotes = {
        "version": "eastmoney-market-quote-v1",
        "data_quality": "fresh",
        "quotes": [
            {
                "stock_code": "300750",
                "stock_name": "宁德时代",
                "change_percent": -2.5,
                "source_provider": "yahoo-chart",
                "source_url": "https://query1.finance.yahoo.com/chart/300750.SZ",
                "retrieved_at": "2026-05-14T12:00:00+00:00",
            }
        ],
    }
    stock_mappings = [
        {
            "stock_code": "300750",
            "narrative_id": "N_NEW_ENERGY",
            "confidence": 0.75,
        }
    ]

    signals = derive_market_quote_signal_events(
        market_quotes_payload=market_quotes,
        stock_mappings=stock_mappings,
        as_of_date="2026-05-14",
    )

    assert signals[0]["signal_type"] == "relative_strength_down"
    assert signals[0]["strength"] == 0.5
    assert signals[0]["confidence"] == 0.4125

    capital_score = calculate_dimension_score(
        "capital_score",
        signals,
        as_of_date="2026-05-14",
        data_quality="partial",
    )
    assert capital_score["risk_signal_count"] == 1
    assert capital_score["score"] < 50
