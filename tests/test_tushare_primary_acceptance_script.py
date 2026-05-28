from pathlib import Path

import pytest
from provider_routing_acceptance_test_support import write_provider_routing_outputs
from scripts import validate_tushare_primary_acceptance


def test_tushare_primary_acceptance_script_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []
    monkeypatch.setenv("TUSHARE_TOKEN", "test-token")

    def fake_run_cli(args: list[str]) -> None:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_tushare_primary_outputs(tmp_path)

    monkeypatch.setattr(
        validate_tushare_primary_acceptance.validate_provider_routing_acceptance,
        "_run_cli",
        fake_run_cli,
    )

    exit_code = validate_tushare_primary_acceptance.main(["--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Tushare primary acceptance passed:" in captured.out
    assert calls == [
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-market-quotes",
            "--include-valuation-snapshots",
            "--valuation-source",
            "provider",
            "--include-financial-metrics",
            "--provider-routing-config",
            str(validate_tushare_primary_acceptance.DEFAULT_ROUTING_CONFIG_PATH),
            "--output-dir",
            str(tmp_path),
        ],
        ["--validate-artifact-contracts", str(tmp_path)],
    ]


def test_tushare_primary_acceptance_requires_token(tmp_path, capsys):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        validate_tushare_primary_acceptance.local_env,
        "get_config_value",
        lambda name: None,
    )
    exit_code = validate_tushare_primary_acceptance.main(["--output-dir", str(tmp_path)])
    monkeypatch.undo()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "TUSHARE_TOKEN must be configured" in captured.err


def test_tushare_primary_acceptance_rejects_tushare_fallback_artifacts(tmp_path):
    _write_tushare_primary_outputs(
        tmp_path,
        layer_fallbacks={
            "valuation_snapshots": {
                "provider": "tushare",
                "fallback_provider": "eastmoney",
            }
        },
    )

    with pytest.raises(validate_tushare_primary_acceptance.AcceptanceError) as exc:
        validate_tushare_primary_acceptance.validate_provider_routing_acceptance.validate_acceptance_outputs(
            tmp_path,
            require_fallback_layers=(),
            forbid_fallback_layers=("valuation_snapshots", "financial_metrics"),
            forbid_provider_unavailable=(
                "tushare-valuation",
                "tushare-financial-metrics",
            ),
            expected_final_providers={
                "market_quotes": validate_tushare_primary_acceptance.validate_provider_routing_acceptance.REAL_QUOTE_PROVIDERS,
                "valuation_snapshots": {"tushare-valuation"},
                "financial_metrics": {"tushare-financial-metrics"},
            },
        )

    assert "unexpected provider fallback event for valuation_snapshots" in str(exc.value)


def test_tushare_primary_acceptance_allows_primary_partial_degradation(tmp_path):
    _write_tushare_primary_outputs(
        tmp_path,
        provider_unavailable={
            "tushare-valuation": "Temporary upstream failure for one stock code",
        },
    )

    validate_tushare_primary_acceptance.validate_provider_routing_acceptance.validate_acceptance_outputs(
        tmp_path,
        require_fallback_layers=(),
        forbid_fallback_layers=("valuation_snapshots", "financial_metrics"),
        expected_final_providers={
            "market_quotes": validate_tushare_primary_acceptance.validate_provider_routing_acceptance.REAL_QUOTE_PROVIDERS,
            "valuation_snapshots": {"tushare-valuation"},
            "financial_metrics": {"tushare-financial-metrics"},
        },
    )


def _write_tushare_primary_outputs(
    output_dir: Path,
    market_provider: str = "akshare-market-quote",
    valuation_provider: str = "tushare-valuation",
    financial_provider: str = "tushare-financial-metrics",
    layer_fallbacks: dict[str, dict[str, str]] | None = None,
    provider_unavailable: dict[str, str] | None = None,
) -> None:
    write_provider_routing_outputs(
        output_dir,
        market_provider=market_provider,
        valuation_provider=valuation_provider,
        financial_provider=financial_provider,
        layer_fallbacks={} if layer_fallbacks is None else layer_fallbacks,
        provider_unavailable={} if provider_unavailable is None else provider_unavailable,
    )
