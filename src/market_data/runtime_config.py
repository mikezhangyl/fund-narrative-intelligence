from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from src import local_env
from src.config import PROJECT_ROOT
from src.providers.tushare_common import DEFAULT_TUSHARE_API_URL, get_tushare_api_url

DEFAULT_DATA_SOURCE_CONFIG_PATH = PROJECT_ROOT / "config" / "data_sources.yaml"


@dataclass(frozen=True)
class SecretPresence:
    name: str
    configured: bool
    source: str
    redacted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderRuntimeStatus:
    provider: str
    enabled: bool
    endpoints: tuple[str, ...]
    pacing_seconds: float | None
    retry_attempts: int | None
    api_url_env: str | None = None
    api_url: str | None = None
    api_url_kind: str | None = None
    gateway_base_url_env: str | None = None
    gateway_base_url: str | None = None
    gateway_configured: bool = False
    token: SecretPresence | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.token is not None:
            payload["token"] = self.token.to_dict()
        return payload


@dataclass(frozen=True)
class MarketDataRuntimeConfig:
    version: str
    generated_at: str
    config_path: str
    default_cache_dir: str
    default_cache_dir_exists: bool
    request_log_path: str
    request_log_path_exists: bool
    gateway: dict[str, Any]
    providers: tuple[ProviderRuntimeStatus, ...]
    excluded_v0: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["providers"] = [provider.to_dict() for provider in self.providers]
        return payload


def inspect_market_data_runtime(
    *,
    config_path: Path | str = DEFAULT_DATA_SOURCE_CONFIG_PATH,
) -> MarketDataRuntimeConfig:
    path = Path(config_path)
    payload = _load_yaml(path)
    section = payload.get("v0_market_data")
    if not isinstance(section, dict):
        raise ValueError(f"{path} missing v0_market_data mapping")

    cache_dir = _project_path(str(section.get("default_cache_dir") or "data/cache"))
    log_path = _project_path(
        str(section.get("request_log_path") or "data/logs/provider_requests.jsonl")
    )
    gateway = _gateway_status(section.get("gateway"))
    providers = _provider_statuses(section.get("providers"))
    excluded = tuple(
        str(item)
        for item in section.get("excluded_v0", [])
        if isinstance(item, str) and item
    )
    return MarketDataRuntimeConfig(
        version="market-data-runtime-config-v1",
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        config_path=str(path),
        default_cache_dir=str(cache_dir),
        default_cache_dir_exists=cache_dir.exists(),
        request_log_path=str(log_path),
        request_log_path_exists=log_path.exists(),
        gateway=gateway,
        providers=providers,
        excluded_v0=excluded,
    )


def _provider_statuses(raw_providers: Any) -> tuple[ProviderRuntimeStatus, ...]:
    if not isinstance(raw_providers, dict):
        raise ValueError("v0_market_data.providers must be a mapping")
    statuses: list[ProviderRuntimeStatus] = []
    for provider_name, raw_provider in sorted(raw_providers.items()):
        if not isinstance(raw_provider, dict):
            raise ValueError(f"provider {provider_name} must be a mapping")
        endpoints = tuple(sorted(str(key) for key in (raw_provider.get("endpoints") or {})))
        status = ProviderRuntimeStatus(
            provider=str(provider_name),
            enabled=bool(raw_provider.get("enabled", False)),
            endpoints=endpoints,
            pacing_seconds=_optional_float(raw_provider.get("pacing_seconds")),
            retry_attempts=_optional_int(raw_provider.get("retry_attempts")),
            gateway_base_url_env=_optional_text(raw_provider.get("gateway_base_url_env")),
            gateway_base_url=resolve_gateway_base_url(
                _optional_text(raw_provider.get("gateway_base_url_env"))
            ),
            gateway_configured=bool(
                resolve_gateway_base_url(
                    _optional_text(raw_provider.get("gateway_base_url_env"))
                )
            ),
        )
        if provider_name == "tushare":
            api_url = get_tushare_api_url()
            token_env = str(raw_provider.get("token_env") or "TUSHARE_TOKEN")
            status = ProviderRuntimeStatus(
                provider=str(provider_name),
                enabled=bool(raw_provider.get("enabled", False)),
                endpoints=endpoints,
                pacing_seconds=_optional_float(raw_provider.get("pacing_seconds")),
                retry_attempts=_optional_int(raw_provider.get("retry_attempts")),
                api_url_env=str(raw_provider.get("api_url_env") or "TUSHARE_API_URL"),
                api_url=api_url,
                api_url_kind=classify_tushare_api_url(api_url),
                gateway_base_url_env=_optional_text(
                    raw_provider.get("gateway_base_url_env")
                ),
                gateway_base_url=resolve_gateway_base_url(
                    _optional_text(raw_provider.get("gateway_base_url_env"))
                ),
                gateway_configured=bool(
                    resolve_gateway_base_url(
                        _optional_text(raw_provider.get("gateway_base_url_env"))
                    )
                ),
                token=resolve_secret_presence(token_env),
            )
        statuses.append(status)
    return tuple(statuses)


def _gateway_status(raw_gateway: Any) -> dict[str, Any]:
    if not isinstance(raw_gateway, dict):
        return {
            "enabled": False,
            "base_url_env": "MARKET_DATA_GATEWAY_URL",
            "base_url_configured": False,
            "base_url_kind": "absent",
        }
    env_name = str(raw_gateway.get("base_url_env") or "MARKET_DATA_GATEWAY_URL")
    base_url = resolve_gateway_base_url(env_name)
    return {
        "enabled": bool(raw_gateway.get("enabled", False)),
        "base_url_env": env_name,
        "base_url_configured": bool(base_url),
        "base_url_kind": classify_gateway_base_url(base_url) if base_url else "absent",
        "contract_path": str(raw_gateway.get("contract_path") or ""),
        "route_mode": str(raw_gateway.get("route_mode") or ""),
        "fallback_to_direct_providers": bool(
            raw_gateway.get("fallback_to_direct_providers", True)
        ),
    }


def classify_tushare_api_url(api_url: str) -> str:
    normalized = api_url.rstrip("/")
    if normalized == DEFAULT_TUSHARE_API_URL.rstrip("/"):
        return "official_default"
    parsed = urlparse(api_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "local_gateway"
    if host.endswith(".local"):
        return "local_gateway"
    return "custom_gateway_or_proxy"


def classify_gateway_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "local_gateway"
    if host.endswith(".local"):
        return "local_gateway"
    return "remote_gateway"


def resolve_gateway_base_url(env_name: str | None = "MARKET_DATA_GATEWAY_URL") -> str | None:
    if not env_name:
        return None
    configured = local_env.get_config_value(env_name)
    if not configured:
        return None
    stripped = configured.strip().rstrip("/")
    return stripped or None


def resolve_secret_presence(name: str) -> SecretPresence:
    local_value = local_env.read_local_env_value(name)
    if local_value is not None:
        return SecretPresence(name=name, configured=True, source="local_env")
    if os.getenv(name):
        return SecretPresence(name=name, configured=True, source="process_env")
    return SecretPresence(name=name, configured=False, source="absent")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"data source config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
