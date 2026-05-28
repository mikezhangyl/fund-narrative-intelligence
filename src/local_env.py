from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENV_PATH = PROJECT_ROOT / ".local.env"


def get_config_value(name: str, *, env_file: Path | None = None) -> str | None:
    local_value = read_local_env_value(name, env_file=env_file)
    if local_value is not None:
        return local_value
    return os.getenv(name)


def read_local_env_value(name: str, *, env_file: Path | None = None) -> str | None:
    path = env_file or LOCAL_ENV_PATH
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        normalized_value = value.strip().strip("\"'")
        if normalized_value == "":
            return None
        return normalized_value
    return None
