import pytest
from src.orchestrator import inspect_provider_foundation


def test_inspect_provider_foundation_returns_mock_layers():
    diagnostics = inspect_provider_foundation("000001")

    foundation = diagnostics["provider_foundation"]

    assert diagnostics["fund_code"] == "000001"
    assert diagnostics["provider_mode"] == "mock"
    assert foundation["effective_data_quality"] == "mock"
    assert foundation["layers"]["holdings"]["is_mock"] is True
    assert foundation["layers"]["evidence"]["is_mock"] is True


def test_inspect_provider_foundation_rejects_invalid_fund_code():
    with pytest.raises(ValueError) as exc:
        inspect_provider_foundation("ABC")

    assert "fund_code" in str(exc.value)
