from __future__ import annotations

from scripts.run_market_data_live_validation import (
    _annotate_status_matrix,
    _endpoint_status_matrix,
    _series_summary,
)
from src.market_data.capabilities import load_data_capability_registry


def test_endpoint_status_matrix_classifies_primary_fallback_unstable_and_disabled():
    reports = [
        {
            "checks": [
                {
                    "source": "tushare",
                    "endpoint": "daily",
                    "capability": "a_share_daily_bars",
                    "availability": True,
                    "latency_ms": 100.0,
                    "row_count": 1,
                    "anti_bot_risk": "low_token_api",
                    "rate_limit_risk": "medium_token_quota_dependent",
                    "failure_reason": None,
                },
                {
                    "source": "akshare",
                    "endpoint": "stock_zt_pool_em+stock_zt_pool_dtgc_em",
                    "capability": "limit_up_down_stats",
                    "availability": True,
                    "latency_ms": 300.0,
                    "row_count": 1,
                    "anti_bot_risk": "medium_public_web_endpoint",
                    "rate_limit_risk": "medium_public_web_endpoint",
                    "failure_reason": None,
                },
                {
                    "source": "akshare",
                    "endpoint": "stock_board_concept_name_em",
                    "capability": "sector_concepts",
                    "availability": True,
                    "latency_ms": 10000.0,
                    "row_count": 486,
                    "anti_bot_risk": "medium_public_web_endpoint",
                    "rate_limit_risk": "medium_public_web_endpoint",
                    "failure_reason": None,
                },
                {
                    "source": "akshare",
                    "endpoint": "stock_zh_a_hist",
                    "capability": "a_share_daily_bars_fallback",
                    "availability": False,
                    "latency_ms": 2000.0,
                    "row_count": 0,
                    "anti_bot_risk": "high_observed_connection_or_blocking_failure",
                    "rate_limit_risk": "medium_public_web_endpoint",
                    "failure_reason": "RemoteDisconnected",
                },
            ]
        },
        {
            "checks": [
                {
                    "source": "tushare",
                    "endpoint": "daily",
                    "capability": "a_share_daily_bars",
                    "availability": True,
                    "latency_ms": 120.0,
                    "row_count": 1,
                    "anti_bot_risk": "low_token_api",
                    "rate_limit_risk": "medium_token_quota_dependent",
                    "failure_reason": None,
                },
                {
                    "source": "akshare",
                    "endpoint": "stock_zt_pool_em+stock_zt_pool_dtgc_em",
                    "capability": "limit_up_down_stats",
                    "availability": True,
                    "latency_ms": 350.0,
                    "row_count": 1,
                    "anti_bot_risk": "medium_public_web_endpoint",
                    "rate_limit_risk": "medium_public_web_endpoint",
                    "failure_reason": None,
                },
                {
                    "source": "akshare",
                    "endpoint": "stock_board_concept_name_em",
                    "capability": "sector_concepts",
                    "availability": False,
                    "latency_ms": 18000.0,
                    "row_count": 0,
                    "anti_bot_risk": "high_observed_connection_or_blocking_failure",
                    "rate_limit_risk": "medium_public_web_endpoint",
                    "failure_reason": "ProxyError",
                },
                {
                    "source": "akshare",
                    "endpoint": "stock_zh_a_hist",
                    "capability": "a_share_daily_bars_fallback",
                    "availability": False,
                    "latency_ms": 1900.0,
                    "row_count": 0,
                    "anti_bot_risk": "high_observed_connection_or_blocking_failure",
                    "rate_limit_risk": "medium_public_web_endpoint",
                    "failure_reason": "ProxyError",
                },
            ]
        },
    ]

    matrix = {
        item["capability"]: item
        for item in _endpoint_status_matrix(reports)
    }

    assert matrix["a_share_daily_bars"]["status"] == "primary"
    assert matrix["limit_up_down_stats"]["status"] == "fallback"
    assert matrix["sector_concepts"]["status"] == "unstable"
    assert matrix["a_share_daily_bars_fallback"]["status"] == "disabled"
    assert matrix["sector_concepts"]["success_count"] == 1
    assert matrix["sector_concepts"]["failure_count"] == 1


def test_series_summary_counts_endpoint_statuses():
    matrix = [
        {"status": "primary"},
        {"status": "fallback"},
        {"status": "fallback"},
        {"status": "unstable"},
        {"status": "disabled"},
    ]

    assert _series_summary(matrix, repeat_count=3) == {
        "repeat_count": 3,
        "endpoint_count": 5,
        "primary_count": 1,
        "fallback_count": 2,
        "unstable_count": 1,
        "disabled_count": 1,
    }


def test_status_matrix_can_be_annotated_from_capability_registry():
    matrix = [
        {
            "source": "tushare",
            "endpoint": "daily",
            "capability": "a_share_daily_bars",
            "status": "primary",
        }
    ]

    annotated = _annotate_status_matrix(
        matrix,
        registry=load_data_capability_registry(),
    )

    assert annotated[0]["dataset_id"] == "a_share_daily_bars"
    assert annotated[0]["configured_status"] == "available"
    assert annotated[0]["gateway_mode"] == "gateway_ready"
    assert annotated[0]["primary_source"]["provider"] == "tushare"
