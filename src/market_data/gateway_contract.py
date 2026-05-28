from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from src.config import PROJECT_ROOT

DEFAULT_GATEWAY_CONTRACT_PATH = PROJECT_ROOT / "config" / "market_data_gateway_contract.yaml"
VALID_METHODS = {"GET", "POST"}


@dataclass(frozen=True)
class GatewayEndpointContract:
    endpoint_id: str
    dataset_id: str
    provider: str
    endpoint: str
    method: str
    path: str
    cache_policy: str
    required_request_fields: tuple[str, ...]
    sample_request: dict[str, Any]
    rows_path: str
    required_response_fields: tuple[str, ...]
    optional_response_fields: tuple[str, ...]
    minimum_rows: int = 0
    maturity: str = "available"
    unstable: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any], *, index: int) -> "GatewayEndpointContract":
        context = f"endpoints[{index}]"
        response = _required_mapping(value, "response", context=context)
        method = _required_text(value, "method", context=context).upper()
        if method not in VALID_METHODS:
            raise ValueError(f"{context}.method must be one of {sorted(VALID_METHODS)}")
        return cls(
            endpoint_id=_required_text(value, "endpoint_id", context=context),
            dataset_id=_required_text(value, "dataset_id", context=context),
            provider=_required_text(value, "provider", context=context),
            endpoint=_required_text(value, "endpoint", context=context),
            method=method,
            path=_required_text(value, "path", context=context),
            cache_policy=_required_text(value, "cache_policy", context=context),
            required_request_fields=tuple(_string_list(value.get("required_request_fields", []), f"{context}.required_request_fields")),
            sample_request=dict(value.get("sample_request") or {}),
            rows_path=_required_text(response, "rows_path", context=f"{context}.response"),
            required_response_fields=tuple(_string_list(response.get("required_fields"), f"{context}.response.required_fields")),
            optional_response_fields=tuple(_string_list(response.get("optional_fields", []), f"{context}.response.optional_fields")),
            minimum_rows=_non_negative_int(response.get("minimum_rows", 0), f"{context}.response.minimum_rows"),
            maturity=str(value.get("maturity") or "available"),
            unstable=bool(value.get("unstable", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GatewayContract:
    version: str
    updated_at: str
    base_path: str
    description: str
    response_envelope: dict[str, Any]
    compatibility: dict[str, Any]
    endpoints: tuple[GatewayEndpointContract, ...]

    @classmethod
    def from_yaml(cls, path: Path | str = DEFAULT_GATEWAY_CONTRACT_PATH) -> "GatewayContract":
        contract_path = Path(path)
        payload = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{contract_path} must contain a mapping")
        endpoints_payload = payload.get("endpoints")
        if not isinstance(endpoints_payload, list) or not endpoints_payload:
            raise ValueError("gateway contract must define at least one endpoint")
        endpoints = tuple(
            GatewayEndpointContract.from_dict(endpoint, index=index)
            for index, endpoint in enumerate(endpoints_payload)
            if isinstance(endpoint, dict)
        )
        contract = cls(
            version=_required_text(payload, "version", context="contract"),
            updated_at=_required_text(payload, "updated_at", context="contract"),
            base_path=_required_text(payload, "base_path", context="contract"),
            description=str(payload.get("description") or ""),
            response_envelope=dict(payload.get("response_envelope") or {}),
            compatibility=dict(payload.get("compatibility") or {}),
            endpoints=endpoints,
        )
        contract.validate()
        return contract

    def validate(self) -> None:
        ids = [endpoint.endpoint_id for endpoint in self.endpoints]
        duplicates = sorted({endpoint_id for endpoint_id in ids if ids.count(endpoint_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate gateway endpoint ids: {', '.join(duplicates)}")
        for endpoint in self.endpoints:
            if not endpoint.path.startswith(self.base_path):
                raise ValueError(
                    f"{endpoint.endpoint_id}.path must start with base_path {self.base_path}"
                )
            sample_fields = set(endpoint.sample_request.get("json") or {})
            sample_fields.update(endpoint.sample_request.get("query") or {})
            missing = [
                field
                for field in endpoint.required_request_fields
                if field not in sample_fields
            ]
            if missing:
                raise ValueError(
                    f"{endpoint.endpoint_id}.sample_request missing required fields: {', '.join(missing)}"
                )

    def endpoint(self, endpoint_id: str) -> GatewayEndpointContract:
        for endpoint in self.endpoints:
            if endpoint.endpoint_id == endpoint_id:
                return endpoint
        raise KeyError(f"unknown gateway endpoint: {endpoint_id}")

    def endpoints_for_provider(self, provider: str) -> tuple[GatewayEndpointContract, ...]:
        return tuple(endpoint for endpoint in self.endpoints if endpoint.provider == provider)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "base_path": self.base_path,
            "description": self.description,
            "response_envelope": self.response_envelope,
            "compatibility": self.compatibility,
            "endpoints": [endpoint.to_dict() for endpoint in self.endpoints],
        }


def load_gateway_contract(
    path: Path | str = DEFAULT_GATEWAY_CONTRACT_PATH,
) -> GatewayContract:
    return GatewayContract.from_yaml(path)


def rows_from_path(payload: dict[str, Any], rows_path: str) -> list[dict[str, Any]]:
    current: Any = payload
    for part in rows_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"response missing rows path: {rows_path}")
        current = current[part]
    if not isinstance(current, list):
        raise ValueError(f"response rows path must resolve to a list: {rows_path}")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(current):
        if not isinstance(row, dict):
            raise ValueError(f"response row {index} must be an object")
        rows.append(row)
    return rows


def missing_required_fields(
    rows: list[dict[str, Any]],
    required_fields: tuple[str, ...],
) -> list[str]:
    missing: set[str] = set()
    for row in rows:
        for field in required_fields:
            if field not in row or row[field] in (None, ""):
                missing.add(field)
    return sorted(missing)


def _required_mapping(value: dict[str, Any], field: str, *, context: str) -> dict[str, Any]:
    nested = value.get(field)
    if not isinstance(nested, dict):
        raise ValueError(f"{context}.{field} must be a mapping")
    return nested


def _required_text(value: dict[str, Any], field: str, *, context: str) -> str:
    text = str(value.get(field) or "").strip()
    if not text:
        raise ValueError(f"{context}.{field} is required")
    return text


def _string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{context} must contain non-empty strings")
    return list(value)


def _non_negative_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{context} must be a non-negative integer")
    return value
