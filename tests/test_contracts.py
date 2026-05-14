import subprocess
import sys
from pathlib import Path

import pytest
from src.errors import FixtureNotFoundError, ProviderContractError
from src.providers.mock import MockDataProvider
from src.validation import (
    validate_fund_payload,
    validate_source_table_artifact_payload,
    validate_valuation_snapshot_payload,
)


def test_mock_provider_lists_available_fund_codes():
    provider = MockDataProvider()

    assert provider.list_fund_codes() == ["000001", "000002", "000003"]


def test_missing_mock_fund_raises_controlled_fixture_error():
    provider = MockDataProvider()

    with pytest.raises(FixtureNotFoundError) as exc:
        provider.get_fund_holdings("999999")

    assert "999999" in str(exc.value)


def test_fund_payload_validation_rejects_missing_provider_metadata():
    payload = {
        "as_of_date": "2026-05-13",
        "fund": {
            "fund_code": "000001",
            "fund_name": "Broken Fund",
            "fund_type": "equity",
            "currency": "USD",
        },
        "holdings": [{"stock_code": "NVDA", "stock_name": "NVIDIA", "weight": 0.1}],
    }

    with pytest.raises(ProviderContractError) as exc:
        validate_fund_payload(payload, fund_code="000001")

    assert "provider_metadata" in str(exc.value)


def test_fund_payload_validation_rejects_holding_weight_outside_range():
    payload = {
        "as_of_date": "2026-05-13",
        "fund": {
            "fund_code": "000001",
            "fund_name": "Broken Fund",
            "fund_type": "equity",
            "currency": "USD",
            "provider_metadata": {
                "provider_name": "mock",
                "provider_version": "mock-v1",
                "source_url": None,
                "as_of_date": "2026-05-13",
                "retrieved_at": "2026-05-13T00:00:00Z",
                "data_quality": "mock",
                "confidence_multiplier": 0.5,
            },
        },
        "holdings": [{"stock_code": "NVDA", "stock_name": "NVIDIA", "weight": 1.5}],
    }

    with pytest.raises(ProviderContractError) as exc:
        validate_fund_payload(payload, fund_code="000001")

    assert "weight" in str(exc.value)


def test_source_table_validation_rejects_layers_that_do_not_match_foundation():
    payload = {
        "version": "source-table-v1",
        "fund_code": "000001",
        "as_of_date": "2026-05-13",
        "provider_foundation": {
            "layers": {"holdings": _source_table_layer()},
            "degradation_events": [],
        },
        "layers": [_source_table_layer(layer="stock_mappings")],
        "degradation_events": [],
    }

    with pytest.raises(ProviderContractError) as exc:
        validate_source_table_artifact_payload(payload)

    assert "layers must match provider_foundation" in str(exc.value)


def test_source_table_validation_rejects_malformed_foundation_layers():
    payload = {
        "version": "source-table-v1",
        "fund_code": "000001",
        "as_of_date": "2026-05-13",
        "provider_foundation": {
            "layers": [],
            "degradation_events": [],
        },
        "layers": [_source_table_layer()],
        "degradation_events": [],
    }

    with pytest.raises(ProviderContractError) as exc:
        validate_source_table_artifact_payload(payload)

    assert "provider_foundation.layers must be an object" in str(exc.value)


def test_source_table_validation_rejects_duplicate_layers():
    payload = {
        "version": "source-table-v1",
        "fund_code": "000001",
        "as_of_date": "2026-05-13",
        "provider_foundation": {
            "layers": {"holdings": _source_table_layer()},
            "degradation_events": [],
        },
        "layers": [
            _source_table_layer(provider_name="bad"),
            _source_table_layer(),
        ],
        "degradation_events": [],
    }

    with pytest.raises(ProviderContractError) as exc:
        validate_source_table_artifact_payload(payload)

    assert "must be unique" in str(exc.value)


def test_source_table_validation_rejects_layer_missing_render_fields():
    layer = _source_table_layer()
    del layer["source_url"]
    payload = {
        "version": "source-table-v1",
        "fund_code": "000001",
        "as_of_date": "2026-05-13",
        "provider_foundation": {
            "layers": {"holdings": layer},
            "degradation_events": [],
        },
        "layers": [layer],
        "degradation_events": [],
    }

    with pytest.raises(ProviderContractError) as exc:
        validate_source_table_artifact_payload(payload)

    assert "missing required fields" in str(exc.value)


def test_valuation_snapshot_validation_rejects_wrong_provider_name():
    payload = _valuation_snapshot_payload(provider_name="not-quote-derived-valuation")

    with pytest.raises(ProviderContractError) as exc:
        validate_valuation_snapshot_payload(payload)

    assert "provider_name must be quote-derived-valuation" in str(exc.value)


def test_valuation_snapshot_validation_rejects_missing_row_provenance():
    payload = _valuation_snapshot_payload()
    payload["valuations"][0]["source_url"] = None

    with pytest.raises(ProviderContractError) as exc:
        validate_valuation_snapshot_payload(payload)

    assert "valuations[0].source_url must be a non-empty string" in str(exc.value)


def _source_table_layer(
    layer: str = "holdings",
    **overrides: object,
) -> dict[str, object]:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": "mock-fixture-provider",
        "provider_version": "mock-v1",
        "data_quality": "mock",
        "source_url": f"mock://fixtures/{layer}",
        "is_mock": True,
        "note": "test layer",
        **overrides,
    }


def _valuation_snapshot_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "version": "valuation-snapshot-v1",
        "provider_name": "quote-derived-valuation",
        "provider_version": "quote-derived-valuation-v1",
        "data_quality": "fresh",
        "source_url": "derived://market-quotes/valuation-context",
        "retrieved_at": "2026-05-14T00:00:00+00:00",
        "valuation_basis": "quote_derived_context",
        "valuations": [
            {
                "stock_code": "NVDA",
                "stock_name": "NVIDIA",
                "latest_price": 106.0,
                "previous_close": 100.0,
                "price_change_percent": 6.0,
                "valuation_pressure": "elevated",
                "source": "market_quote",
                "source_provider": "eastmoney",
                "source_url": "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                "retrieved_at": "2026-05-14T00:00:00+00:00",
            }
        ],
        "missing_stock_codes": [],
    }
    return {**payload, **overrides}


def test_cli_lists_available_fixtures():
    command = [sys.executable, "-m", "src.main", "--list-fixtures"]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert "000001" in result.stdout


def test_cli_missing_fund_returns_clear_controlled_error(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "999999",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 1
    assert "No mock fixture found for fund code 999999" in result.stderr
    assert not list(Path(tmp_path).glob("*"))
