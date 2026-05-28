from __future__ import annotations

import json

from scripts import build_market_data_reliability_report as reliability


def test_build_reliability_report_marks_degraded_with_live_and_stress_failures():
    report = reliability.build_reliability_report(
        capability_report={
            "summary": {
                "dataset_count": 3,
                "dataset_status_counts": {"available": 2, "planned": 1},
                "gateway_mode_counts": {"gateway_ready": 2, "gateway_owned": 1},
                "missing_or_planned_datasets": ["cyq_chips"],
            },
            "analysis_readiness": {
                "market_breadth_ma20": {"can_run": True, "warnings": []},
                "cost_basis_analysis": {"can_run": False, "warnings": []},
                "sector_rotation_scan": {
                    "can_run": True,
                    "warnings": ["unstable_dataset:sector_concepts"],
                },
            },
        },
        runtime_report={
            "default_cache_dir_exists": True,
            "request_log_path_exists": True,
            "gateway": {
                "base_url_configured": False,
                "base_url_kind": "absent",
            },
            "providers": [
                {
                    "provider": "tushare",
                    "api_url_kind": "official_default",
                    "token": {"configured": True, "source": "local_env"},
                }
            ],
        },
        live_report={
            "generated_at": "2026-05-25T00:00:00+08:00",
            "checks": [
                {"capability": "daily", "availability": True},
                {
                    "capability": "sector_concepts",
                    "availability": False,
                    "source": "akshare",
                    "endpoint": "stock_board_concept_name_em",
                    "failure_reason": "proxy disconnected",
                },
            ],
        },
        stress_report={
            "generated_at": "2026-05-25T00:00:00+08:00",
            "status": "completed_with_failures",
            "summary": {
                "test_count": 3,
                "request_volume": 6,
                "rows_returned": 18,
                "failure_count": 1,
            },
            "results": {
                "sector": {
                    "failure_count": 1,
                    "failure_reasons": ["sector endpoint blocked"],
                }
            },
        },
    )

    assert report["status"] == "degraded"
    assert report["live_validation"]["failed_checks"] == 1
    assert report["stress"]["failure_count"] == 1
    assert report["analysis_readiness"]["blocked"] == ["cost_basis_analysis"]
    assert any("TUSHARE_API_URL" in item for item in report["recommendations"])


def test_render_reliability_report_json_and_markdown():
    report = {
        "version": "market-data-reliability-report-v1",
        "generated_at": "2026-05-25T00:00:00+08:00",
        "status": "ready",
        "runtime": {
            "tushare_api_url_kind": "local_gateway",
            "tushare_token_source": "local_env",
            "gateway_configured": True,
            "gateway_url_kind": "local_gateway",
            "cache_dir_exists": True,
        },
        "capabilities": {"dataset_count": 1},
        "analysis_readiness": {"runnable": 1, "total": 1, "blocked": []},
        "live_validation": {
            "available_checks": 1,
            "total_checks": 1,
            "failed_capabilities": [],
        },
        "stress": {"request_volume": 1, "failure_count": 0},
        "recommendations": ["Keep running controlled probes."],
    }

    markdown = reliability.render_report(report, output_format="markdown")
    payload = json.loads(reliability.render_report(report, output_format="json"))

    assert "# V0 Market Data Reliability Report" in markdown
    assert "- None" in markdown
    assert payload["status"] == "ready"
