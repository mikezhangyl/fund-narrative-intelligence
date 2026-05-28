from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CAPABILITY_CONFIG_PATH = Path("config/data_capabilities.yaml")

_VALID_DATASET_STATUSES = {"available", "unstable", "missing", "planned", "disabled"}
_VALID_DIFFICULTIES = {"low", "medium", "high", "unknown"}
_VALID_GATEWAY_MODES = {
    "direct_only",
    "gateway_ready",
    "gateway_planned",
    "gateway_owned",
}


@dataclass(frozen=True)
class DataSourceRef:
    provider: str
    endpoint: str
    access_mode: str
    current_status: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any], *, context: str) -> DataSourceRef:
        provider = _required_text(value, "provider", context=context)
        endpoint = _required_text(value, "endpoint", context=context)
        access_mode = _required_text(value, "access_mode", context=context)
        current_status = _optional_text(value, "current_status")
        return cls(
            provider=provider,
            endpoint=endpoint,
            access_mode=access_mode,
            current_status=current_status,
        )

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(frozen=True)
class DatasetCapability:
    dataset_id: str
    description: str
    current_status: str
    acquisition_difficulty: str
    gateway_mode: str
    required_fields: tuple[str, ...]
    freshness: str
    primary_source: DataSourceRef
    fallback_sources: tuple[DataSourceRef, ...]
    validation_probe_capability: str | None
    risks: dict[str, Any]
    analysis_use_cases: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_mapping(
        cls,
        dataset_id: str,
        value: dict[str, Any],
    ) -> DatasetCapability:
        context = f"dataset {dataset_id}"
        current_status = _required_text(value, "current_status", context=context)
        if current_status not in _VALID_DATASET_STATUSES:
            raise ValueError(
                f"{context} current_status must be one of {sorted(_VALID_DATASET_STATUSES)}"
            )
        acquisition_difficulty = _required_text(
            value,
            "acquisition_difficulty",
            context=context,
        )
        if acquisition_difficulty not in _VALID_DIFFICULTIES:
            raise ValueError(
                f"{context} acquisition_difficulty must be one of {sorted(_VALID_DIFFICULTIES)}"
            )
        gateway_mode = _required_text(value, "gateway_mode", context=context)
        if gateway_mode not in _VALID_GATEWAY_MODES:
            raise ValueError(
                f"{context} gateway_mode must be one of {sorted(_VALID_GATEWAY_MODES)}"
            )
        primary_source = DataSourceRef.from_mapping(
            _required_mapping(value, "primary_source", context=context),
            context=f"{context} primary_source",
        )
        fallback_sources = tuple(
            DataSourceRef.from_mapping(
                item,
                context=f"{context} fallback_sources[{index}]",
            )
            for index, item in enumerate(
                _optional_mapping_list(value, "fallback_sources", context=context)
            )
        )
        validation = _optional_mapping(value, "validation")
        return cls(
            dataset_id=dataset_id,
            description=_required_text(value, "description", context=context),
            current_status=current_status,
            acquisition_difficulty=acquisition_difficulty,
            gateway_mode=gateway_mode,
            required_fields=tuple(_required_text_list(value, "required_fields", context=context)),
            freshness=_required_text(value, "freshness", context=context),
            primary_source=primary_source,
            fallback_sources=fallback_sources,
            validation_probe_capability=_optional_text(
                validation,
                "live_probe_capability",
            )
            if validation
            else None,
            risks=dict(_optional_mapping(value, "risks") or {}),
            analysis_use_cases=tuple(
                _optional_text_list(value, "analysis_use_cases", context=context)
            ),
            notes=tuple(_optional_text_list(value, "notes", context=context)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "current_status": self.current_status,
            "acquisition_difficulty": self.acquisition_difficulty,
            "gateway_mode": self.gateway_mode,
            "required_fields": list(self.required_fields),
            "freshness": self.freshness,
            "primary_source": self.primary_source.to_dict(),
            "fallback_sources": [source.to_dict() for source in self.fallback_sources],
            "validation": _drop_none(
                {"live_probe_capability": self.validation_probe_capability}
            ),
            "risks": self.risks,
            "analysis_use_cases": list(self.analysis_use_cases),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class AnalysisCapability:
    capability_id: str
    description: str
    complexity: str
    implementation_status: str
    required_datasets: tuple[str, ...]
    output_metrics: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_mapping(
        cls,
        capability_id: str,
        value: dict[str, Any],
    ) -> AnalysisCapability:
        context = f"analysis_capability {capability_id}"
        return cls(
            capability_id=capability_id,
            description=_required_text(value, "description", context=context),
            complexity=_required_text(value, "complexity", context=context),
            implementation_status=_required_text(
                value,
                "implementation_status",
                context=context,
            ),
            required_datasets=tuple(
                _required_text_list(value, "required_datasets", context=context)
            ),
            output_metrics=tuple(
                _optional_text_list(value, "output_metrics", context=context)
            ),
            notes=tuple(_optional_text_list(value, "notes", context=context)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "complexity": self.complexity,
            "implementation_status": self.implementation_status,
            "required_datasets": list(self.required_datasets),
            "output_metrics": list(self.output_metrics),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class DataCapabilityRegistry:
    version: str
    updated_at: str
    purpose: str
    datasets: dict[str, DatasetCapability]
    analysis_capabilities: dict[str, AnalysisCapability]

    @classmethod
    def from_yaml(cls, path: Path | str) -> DataCapabilityRegistry:
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{config_path} must contain a YAML mapping")
        datasets_raw = _required_mapping(raw, "datasets", context=str(config_path))
        analysis_raw = _required_mapping(
            raw,
            "analysis_capabilities",
            context=str(config_path),
        )
        datasets = {
            str(dataset_id): DatasetCapability.from_mapping(str(dataset_id), value)
            for dataset_id, value in datasets_raw.items()
            if _ensure_mapping(value, context=f"dataset {dataset_id}")
        }
        analysis_capabilities = {
            str(capability_id): AnalysisCapability.from_mapping(
                str(capability_id),
                value,
            )
            for capability_id, value in analysis_raw.items()
            if _ensure_mapping(value, context=f"analysis_capability {capability_id}")
        }
        registry = cls(
            version=_required_text(raw, "version", context=str(config_path)),
            updated_at=_required_text(raw, "updated_at", context=str(config_path)),
            purpose=_required_text(raw, "purpose", context=str(config_path)),
            datasets=datasets,
            analysis_capabilities=analysis_capabilities,
        )
        registry.validate()
        return registry

    def validate(self) -> None:
        if not self.datasets:
            raise ValueError("data capability registry must define at least one dataset")
        if not self.analysis_capabilities:
            raise ValueError(
                "data capability registry must define at least one analysis capability"
            )
        known_datasets = set(self.datasets)
        for capability in self.analysis_capabilities.values():
            missing = sorted(set(capability.required_datasets) - known_datasets)
            if missing:
                raise ValueError(
                    f"analysis capability {capability.capability_id} references "
                    f"unknown datasets: {', '.join(missing)}"
                )

    def dataset(self, dataset_id: str) -> DatasetCapability:
        try:
            return self.datasets[dataset_id]
        except KeyError as exc:
            raise KeyError(f"unknown dataset capability: {dataset_id}") from exc

    def analysis_capability(self, capability_id: str) -> AnalysisCapability:
        try:
            return self.analysis_capabilities[capability_id]
        except KeyError as exc:
            raise KeyError(f"unknown analysis capability: {capability_id}") from exc

    def missing_datasets_for_analysis(self, capability_id: str) -> list[str]:
        capability = self.analysis_capability(capability_id)
        return [
            dataset_id
            for dataset_id in capability.required_datasets
            if self.datasets[dataset_id].current_status in {"missing", "planned", "disabled"}
        ]

    def analysis_readiness(self, capability_id: str) -> dict[str, Any]:
        capability = self.analysis_capability(capability_id)
        blockers: list[str] = []
        warnings: list[str] = []
        datasets: list[dict[str, Any]] = []
        for dataset_id in capability.required_datasets:
            dataset = self.datasets[dataset_id]
            datasets.append(
                {
                    "dataset_id": dataset.dataset_id,
                    "status": dataset.current_status,
                    "difficulty": dataset.acquisition_difficulty,
                    "gateway_mode": dataset.gateway_mode,
                    "primary_source": dataset.primary_source.to_dict(),
                }
            )
            if dataset.current_status in {"missing", "planned", "disabled"}:
                blockers.append(f"{dataset.current_status}_dataset:{dataset_id}")
            elif dataset.current_status == "unstable":
                warnings.append(f"unstable_dataset:{dataset_id}")
        return {
            "capability_id": capability.capability_id,
            "implementation_status": capability.implementation_status,
            "complexity": capability.complexity,
            "can_run": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "datasets": datasets,
        }

    def dataset_for_probe_capability(self, probe_capability: str) -> DatasetCapability | None:
        for dataset in self.datasets.values():
            if dataset.validation_probe_capability == probe_capability:
                return dataset
        return None

    def annotate_probe_matrix(
        self,
        matrix: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        annotated: list[dict[str, Any]] = []
        for item in matrix:
            dataset = self.dataset_for_probe_capability(str(item.get("capability")))
            if dataset is None:
                annotated.append(dict(item))
                continue
            annotated.append(
                {
                    **item,
                    "dataset_id": dataset.dataset_id,
                    "configured_status": dataset.current_status,
                    "acquisition_difficulty": dataset.acquisition_difficulty,
                    "gateway_mode": dataset.gateway_mode,
                    "primary_source": dataset.primary_source.to_dict(),
                }
            )
        return annotated

    def summary(self) -> dict[str, Any]:
        status_counts = Counter(
            dataset.current_status for dataset in self.datasets.values()
        )
        difficulty_counts = Counter(
            dataset.acquisition_difficulty for dataset in self.datasets.values()
        )
        gateway_counts = Counter(dataset.gateway_mode for dataset in self.datasets.values())
        implementation_counts = Counter(
            capability.implementation_status
            for capability in self.analysis_capabilities.values()
        )
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "dataset_count": len(self.datasets),
            "analysis_capability_count": len(self.analysis_capabilities),
            "dataset_status_counts": dict(sorted(status_counts.items())),
            "difficulty_counts": dict(sorted(difficulty_counts.items())),
            "gateway_mode_counts": dict(sorted(gateway_counts.items())),
            "analysis_implementation_counts": dict(
                sorted(implementation_counts.items())
            ),
            "missing_or_planned_datasets": [
                dataset.dataset_id
                for dataset in self.datasets.values()
                if dataset.current_status in {"missing", "planned", "disabled"}
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "purpose": self.purpose,
            "summary": self.summary(),
            "datasets": {
                dataset_id: dataset.to_dict()
                for dataset_id, dataset in self.datasets.items()
            },
            "analysis_capabilities": {
                capability_id: capability.to_dict()
                for capability_id, capability in self.analysis_capabilities.items()
            },
            "analysis_readiness": {
                capability_id: self.analysis_readiness(capability_id)
                for capability_id in self.analysis_capabilities
            },
        }


def load_data_capability_registry(
    path: Path | str = DEFAULT_CAPABILITY_CONFIG_PATH,
) -> DataCapabilityRegistry:
    return DataCapabilityRegistry.from_yaml(path)


def _required_text(
    value: dict[str, Any],
    key: str,
    *,
    context: str,
) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{context} requires non-empty string field {key}")
    return item.strip()


def _optional_text(value: dict[str, Any] | None, key: str) -> str | None:
    if not value:
        return None
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"optional field {key} must be a non-empty string when set")
    return item.strip()


def _required_text_list(
    value: dict[str, Any],
    key: str,
    *,
    context: str,
) -> list[str]:
    items = value.get(key)
    if not isinstance(items, list) or not items:
        raise ValueError(f"{context} requires non-empty list field {key}")
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise ValueError(f"{context} field {key} must contain only non-empty strings")
    return [item.strip() for item in items]


def _optional_text_list(
    value: dict[str, Any],
    key: str,
    *,
    context: str,
) -> list[str]:
    items = value.get(key, [])
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError(f"{context} field {key} must be a list")
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise ValueError(f"{context} field {key} must contain only non-empty strings")
    return [item.strip() for item in items]


def _required_mapping(
    value: dict[str, Any],
    key: str,
    *,
    context: str,
) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict) or not item:
        raise ValueError(f"{context} requires non-empty mapping field {key}")
    return item


def _optional_mapping(value: dict[str, Any], key: str) -> dict[str, Any] | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, dict):
        raise ValueError(f"field {key} must be a mapping when set")
    return item


def _optional_mapping_list(
    value: dict[str, Any],
    key: str,
    *,
    context: str,
) -> list[dict[str, Any]]:
    items = value.get(key, [])
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError(f"{context} field {key} must be a list")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{context} field {key}[{index}] must be a mapping")
    return items


def _ensure_mapping(value: Any, *, context: str) -> bool:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping")
    return True


def _drop_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}
