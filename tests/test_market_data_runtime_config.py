from __future__ import annotations

import json

import pytest
from scripts import report_market_data_runtime
from src.market_data import runtime_config


def test_runtime_config_reports_official_default_and_redacted_token(monkeypatch, tmp_path):
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text(
        """
v0_market_data:
  default_cache_dir: data/cache
  request_log_path: data/logs/provider_requests.jsonl
  gateway:
    enabled: true
    base_url_env: MARKET_DATA_GATEWAY_URL
    route_mode: normalized_rest
    fallback_to_direct_providers: true
  providers:
    tushare:
      enabled: true
      api_url_env: TUSHARE_API_URL
      gateway_base_url_env: MARKET_DATA_GATEWAY_URL
      default_api_url: https://api.tushare.pro
      token_env: TUSHARE_TOKEN
      pacing_seconds: 0.2
      retry_attempts: 2
      endpoints:
        daily: stock daily OHLCV
        trade_cal: trading calendar
    akshare:
      enabled: true
      pacing_seconds: 0.5
      retry_attempts: 2
      endpoints:
        stock_board_concept_name_em: concept sectors
  excluded_v0:
    - browser_automation
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_config.local_env, "get_config_value", lambda name: None)
    monkeypatch.setattr(
        runtime_config.local_env,
        "read_local_env_value",
        lambda name: "secret-token" if name == "TUSHARE_TOKEN" else None,
    )

    report = runtime_config.inspect_market_data_runtime(config_path=config_path).to_dict()
    tushare = _provider(report, "tushare")

    assert tushare["api_url"] == "https://api.tushare.pro"
    assert tushare["api_url_kind"] == "official_default"
    assert tushare["token"] == {
        "name": "TUSHARE_TOKEN",
        "configured": True,
        "source": "local_env",
        "redacted": True,
    }
    assert "secret-token" not in json.dumps(report)
    assert "trade_cal" in tushare["endpoints"]
    assert report["gateway"]["base_url_configured"] is False
    assert tushare["gateway_configured"] is False


def test_runtime_config_classifies_local_gateway(monkeypatch, tmp_path):
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text(
        """
v0_market_data:
  providers:
    tushare:
      enabled: true
      token_env: TUSHARE_TOKEN
      endpoints: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runtime_config.local_env,
        "get_config_value",
        lambda name: "http://127.0.0.1:8700"
        if name == "TUSHARE_API_URL"
        else "http://127.0.0.1:8700"
        if name == "MARKET_DATA_GATEWAY_URL"
        else None,
    )
    monkeypatch.setattr(
        runtime_config.local_env,
        "read_local_env_value",
        lambda name: None,
    )

    report = runtime_config.inspect_market_data_runtime(config_path=config_path).to_dict()
    tushare = _provider(report, "tushare")

    assert tushare["api_url_kind"] == "local_gateway"
    assert tushare["gateway_configured"] is False
    assert tushare["token"]["configured"] is False
    assert tushare["token"]["source"] == "absent"


def test_runtime_report_markdown_and_json(monkeypatch, tmp_path):
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text(
        """
v0_market_data:
  providers:
    akshare:
      enabled: true
      endpoints:
        stock_zt_pool_em: limit up
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_config.local_env, "get_config_value", lambda name: None)
    monkeypatch.setattr(runtime_config.local_env, "read_local_env_value", lambda name: None)

    markdown = report_market_data_runtime.build_report(
        config_path=config_path,
        output_format="markdown",
    )
    payload = json.loads(
        report_market_data_runtime.build_report(
            config_path=config_path,
            output_format="json",
        )
    )

    assert "# Market Data Runtime Configuration" in markdown
    assert "| akshare | True | n/a | False | absent | 1 |" in markdown
    assert payload["providers"][0]["provider"] == "akshare"


def test_runtime_config_rejects_missing_provider_mapping(tmp_path):
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text("v0_market_data: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="providers"):
        runtime_config.inspect_market_data_runtime(config_path=config_path)


def _provider(report: dict, name: str) -> dict:
    return next(provider for provider in report["providers"] if provider["provider"] == name)
