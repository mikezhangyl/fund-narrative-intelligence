import subprocess
import sys
from pathlib import Path

import pytest
from src.errors import FixtureNotFoundError, ProviderContractError
from src.providers.mock import MockDataProvider
from src.validation import validate_fund_payload


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
