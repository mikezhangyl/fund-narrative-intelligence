from __future__ import annotations

import json

import pytest
from scripts import validate_market_data_gateway_contract as conformance
from src.market_data.gateway_contract import (
    load_gateway_contract,
    missing_required_fields,
    rows_from_path,
)


def test_gateway_contract_loads_multi_source_endpoints():
    contract = load_gateway_contract()

    endpoint_ids = {endpoint.endpoint_id for endpoint in contract.endpoints}

    assert contract.version == "market-data-gateway-contract-v1"
    assert "tushare_daily" in endpoint_ids
    assert "akshare_sector_concepts" in endpoint_ids
    assert "eastmoney_market_quote" in endpoint_ids
    assert "local_gateway_cyq_chips" in endpoint_ids
    assert "gateway_stock_sector_memberships" in endpoint_ids
    assert contract.endpoint("tushare_trade_cal").provider == "tushare"
    assert contract.endpoints_for_provider("eastmoney")
    assert contract.compatibility["tushare_native_post"]["path"] == "/tushare"
    assert contract.endpoint("akshare_sector_concepts").minimum_rows == 1
    assert contract.endpoint("gateway_sector_constituents").maturity == "available"
    assert contract.endpoint("gateway_etf_basic").maturity == "available"
    assert contract.endpoint("gateway_index_constituents").maturity == "available"
    assert contract.endpoint("gateway_margin_summary").maturity == "available"
    assert contract.endpoint("gateway_margin_detail").maturity == "available"
    assert contract.endpoint("gateway_earnings_calendar").maturity == "available"
    assert contract.endpoint("gateway_stock_sector_memberships").method == "POST"
    assert contract.endpoint("gateway_fund_profile").maturity == "available"
    assert contract.endpoint("gateway_fund_holdings").maturity == "available"
    assert contract.endpoint("gateway_fund_holdings").dataset_id == "fund_holdings"


def test_gateway_contract_rows_and_missing_field_helpers():
    payload = {"data": {"rows": [{"symbol": "600519.SH", "close": 1.0}]}}

    rows = rows_from_path(payload, "data.rows")

    assert rows == [{"symbol": "600519.SH", "close": 1.0}]
    assert missing_required_fields(rows, ("symbol", "trade_date")) == ["trade_date"]
    with pytest.raises(ValueError, match="rows path"):
        rows_from_path({}, "data.rows")


def test_gateway_conformance_passes_with_fake_fetcher():
    contract = load_gateway_contract()

    def fetcher(endpoint, base_url, timeout_seconds):
        del base_url, timeout_seconds
        row = {field: "value" for field in endpoint.required_response_fields}
        return 200, {
            "data": {"rows": [row]},
            "meta": {
                "provider": endpoint.provider,
                "endpoint": endpoint.endpoint,
                "cache": {"hit": True, "mode": "cache"},
                "generated_at": "2026-05-25T00:00:00+08:00",
            },
        }

    report = conformance.run_gateway_conformance(
        contract=contract,
        base_url="http://localhost:8700",
        endpoint_ids=("tushare_daily", "eastmoney_market_quote"),
        fetcher=fetcher,
    )

    assert report["summary"] == {
        "total_checks": 2,
        "passed_checks": 2,
        "failed_checks": 0,
    }
    assert all(check["status"] == "passed" for check in report["checks"])


def test_gateway_conformance_records_failures_for_selected_available_endpoints():
    contract = load_gateway_contract()

    def fetcher(endpoint, base_url, timeout_seconds):
        del base_url, timeout_seconds
        if endpoint.endpoint_id == "akshare_sector_concepts":
            return 200, {"data": {"rows": [{"sector_name": "机器人"}]}}
        return 500, {"error": {"code": "bad_gateway", "message": "upstream failed"}}

    report = conformance.run_gateway_conformance(
        contract=contract,
        base_url="http://localhost:8700",
        endpoint_ids=("akshare_sector_concepts", "eastmoney_northbound_capital"),
        fetcher=fetcher,
    )

    assert report["summary"]["total_checks"] == 2
    checks_by_endpoint = {check["endpoint_id"]: check for check in report["checks"]}
    assert checks_by_endpoint["akshare_sector_concepts"]["status"] == "failed"
    assert (
        "missing required response fields"
        in checks_by_endpoint["akshare_sector_concepts"]["failure_reason"]
    )
    assert checks_by_endpoint["eastmoney_northbound_capital"]["status"] == "failed"
    assert "HTTP status 500" in checks_by_endpoint["eastmoney_northbound_capital"]["failure_reason"]


def test_gateway_conformance_records_minimum_row_failure():
    contract = load_gateway_contract()

    def fetcher(endpoint, base_url, timeout_seconds):
        del endpoint, base_url, timeout_seconds
        return 200, {"data": {"rows": []}}

    report = conformance.run_gateway_conformance(
        contract=contract,
        base_url="http://localhost:8700",
        endpoint_ids=("akshare_sector_concepts",),
        fetcher=fetcher,
    )

    assert report["summary"]["failed_checks"] == 1
    assert report["checks"][0]["row_count"] == 0
    assert "expected at least 1 row" in report["checks"][0]["failure_reason"]


def test_tushare_facade_conformance_passes_with_fake_fetcher():
    contract = load_gateway_contract()
    captured_bodies = {}

    def facade_fetcher(endpoint, url, request_body, timeout_seconds):
        del timeout_seconds
        captured_bodies[endpoint.endpoint_id] = request_body
        assert url == "http://localhost:8700/tushare"

        if endpoint.endpoint_id == "tushare_trade_cal":
            return 200, {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": ["exchange", "cal_date", "is_open"],
                    "items": [["SSE", "20260522", 1]],
                },
            }
        return 200, {
            "code": 0,
            "msg": "",
            "data": {
                "fields": ["ts_code", "trade_date", "close", "vol"],
                "items": [["600519.SH", "20260522", 1700.0, 1200.0]],
            },
        }

    report = conformance.run_gateway_conformance(
        contract=contract,
        base_url="http://localhost:8700",
        endpoint_ids=("tushare_daily", "tushare_trade_cal"),
        mode="tushare-facade",
        facade_fetcher=facade_fetcher,
    )

    assert report["mode"] == "tushare-facade"
    assert report["summary"] == {
        "total_checks": 2,
        "passed_checks": 2,
        "failed_checks": 0,
    }
    assert {check["surface"] for check in report["checks"]} == {"tushare_facade"}
    assert captured_bodies["tushare_daily"] == {
        "api_name": "daily",
        "token": "local-gateway-token-ignored",
        "params": {
            "ts_code": "600519.SH",
            "start_date": "20260522",
            "end_date": "20260522",
        },
        "fields": "ts_code,trade_date,close,vol",
    }
    assert captured_bodies["tushare_trade_cal"]["params"] == {
        "exchange": "SSE",
        "start_date": "20260522",
        "end_date": "20260522",
    }


def test_tushare_facade_conformance_records_schema_failure():
    contract = load_gateway_contract()

    def facade_fetcher(endpoint, url, request_body, timeout_seconds):
        del endpoint, url, request_body, timeout_seconds
        return 200, {
            "code": 0,
            "msg": "",
            "data": {
                "fields": ["ts_code", "trade_date", "close"],
                "items": [["600519.SH", "20260522", 1700.0]],
            },
        }

    report = conformance.run_gateway_conformance(
        contract=contract,
        base_url="http://localhost:8700",
        endpoint_ids=("tushare_daily",),
        mode="tushare-facade",
        facade_fetcher=facade_fetcher,
    )

    assert report["summary"]["failed_checks"] == 1
    assert report["checks"][0]["surface"] == "tushare_facade"
    assert report["checks"][0]["missing_fields"] == ("vol",)
    assert "missing required response fields" in report["checks"][0]["failure_reason"]


def test_gateway_conformance_all_mode_combines_normalized_and_facade_checks():
    contract = load_gateway_contract()

    def fetcher(endpoint, base_url, timeout_seconds):
        del base_url, timeout_seconds
        row = {field: "value" for field in endpoint.required_response_fields}
        return 200, {"data": {"rows": [row]}}

    def facade_fetcher(endpoint, url, request_body, timeout_seconds):
        del endpoint, url, request_body, timeout_seconds
        return 200, {
            "code": 0,
            "msg": "",
            "data": {
                "fields": ["ts_code", "trade_date", "close", "vol"],
                "items": [["600519.SH", "20260522", 1700.0, 1200.0]],
            },
        }

    report = conformance.run_gateway_conformance(
        contract=contract,
        base_url="http://localhost:8700",
        endpoint_ids=("tushare_daily", "eastmoney_market_quote"),
        mode="all",
        fetcher=fetcher,
        facade_fetcher=facade_fetcher,
    )

    assert report["summary"] == {
        "total_checks": 3,
        "passed_checks": 3,
        "failed_checks": 0,
    }
    assert [check["surface"] for check in report["checks"]] == [
        "normalized",
        "normalized",
        "tushare_facade",
    ]


def test_gateway_conformance_renderers():
    report = {
        "version": "market-data-gateway-conformance-v1",
        "generated_at": "2026-05-25T00:00:00+08:00",
        "base_url": "http://localhost:8700",
        "contract_version": "market-data-gateway-contract-v1",
        "mode": "normalized",
        "summary": {"total_checks": 1, "passed_checks": 1, "failed_checks": 0},
        "checks": [
            {
                "endpoint_id": "tushare_daily",
                "provider": "tushare",
                "dataset_id": "a_share_daily_bars",
                "surface": "normalized",
                "status": "passed",
                "row_count": 1,
            }
        ],
    }

    markdown = conformance.render_report(report, output_format="markdown")
    payload = json.loads(conformance.render_report(report, output_format="json"))

    assert "# Market Data Gateway Conformance" in markdown
    assert payload["summary"]["passed_checks"] == 1
