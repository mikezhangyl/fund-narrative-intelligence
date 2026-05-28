from pathlib import Path

from src.local_env import get_config_value, read_local_env_value


def test_read_local_env_value_returns_none_for_missing_or_empty_keys(tmp_path: Path):
    env_file = tmp_path / ".local.env"
    env_file.write_text(
        "# comment only\nTUSHARE_TOKEN=\nOTHER_KEY=value\n",
        encoding="utf-8",
    )

    assert read_local_env_value("MISSING_KEY", env_file=env_file) is None
    assert read_local_env_value("TUSHARE_TOKEN", env_file=env_file) is None


def test_get_config_value_prefers_local_env_over_process_env(
    tmp_path: Path,
    monkeypatch,
):
    env_file = tmp_path / ".local.env"
    env_file.write_text("TUSHARE_TOKEN=local-token\n", encoding="utf-8")
    monkeypatch.setenv("TUSHARE_TOKEN", "process-token")

    assert get_config_value("TUSHARE_TOKEN", env_file=env_file) == "local-token"


def test_get_config_value_falls_back_to_process_env(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".local.env"
    env_file.write_text("# no token here\n", encoding="utf-8")
    monkeypatch.setenv("TUSHARE_TOKEN", "process-token")

    assert get_config_value("TUSHARE_TOKEN", env_file=env_file) == "process-token"
