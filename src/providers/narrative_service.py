from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from src.config import (
    DEFAULT_CANDIDATE_NARRATIVE_EVENTS_PATH,
    DEFAULT_MAPPING_EVIDENCE_PACKS_PATH,
    PROJECT_ROOT,
)
from src.errors import FixtureNotFoundError
from src.providers.intelligence import (
    NarrativeRegistryProvider,
    ReviewedNarrativeRegistryProvider,
    ReviewedStockNarrativeMappingProvider,
    StockNarrativeMappingProvider,
)


class NarrativeDataProvider(Protocol):
    def get_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_report_inputs(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        raise NotImplementedError


@dataclass(frozen=True)
class LocalNarrativePrototypeProvider:
    registry_provider: NarrativeRegistryProvider = field(
        default_factory=ReviewedNarrativeRegistryProvider
    )
    mapping_provider: StockNarrativeMappingProvider = field(
        default_factory=ReviewedStockNarrativeMappingProvider
    )
    evidence_packs_path: Path = DEFAULT_MAPPING_EVIDENCE_PACKS_PATH
    candidate_events_path: Path = DEFAULT_CANDIDATE_NARRATIVE_EVENTS_PATH

    provider_name = "local-narrative-prototype-provider"
    provider_version = "local-narrative-prototype-v1"
    source = "local_prototype"

    def get_snapshot(self) -> dict[str, Any]:
        registry = self.registry_provider.get_narrative_registry()
        mappings = self.mapping_provider.get_stock_narrative_mappings()
        evidence_packs = _load_evidence_packs(self.evidence_packs_path)
        candidate_events = _load_candidate_events(self.candidate_events_path)
        return {
            "status": "available",
            "source": self.source,
            "provider": self.provider_name,
            "provider_version": self.provider_version,
            "narrative_registry": deepcopy(registry),
            "stock_narrative_mappings": deepcopy(mappings),
            "mapping_evidence_packs": deepcopy(evidence_packs),
            "candidate_intake_events": deepcopy(candidate_events),
            "provider_layers": self.get_provider_layers(),
            "warnings": [
                {
                    "code": "LOCAL_PROTOTYPE_FALLBACK",
                    "message": (
                        "Using FNI local narrative prototype files; this is not "
                        "authoritative narrative-service storage."
                    ),
                }
            ],
            "diagnostics": {
                "local_fallback": True,
                "service_ready": False,
                "registry_count": len(registry.get("narratives", [])),
                "candidate_registry_count": len(
                    registry.get("candidate_narratives", [])
                ),
                "stock_mapping_count": len(mappings),
                "evidence_pack_count": len(evidence_packs.get("packs", [])),
                "candidate_event_count": len(candidate_events.get("events", [])),
            },
        }

    def get_report_inputs(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        snapshot = self.get_snapshot()
        return (
            deepcopy(snapshot["narrative_registry"]),
            deepcopy(snapshot["stock_narrative_mappings"]),
        )

    def get_provider_layers(self) -> dict[str, dict[str, Any]]:
        return {
            "narrative_registry": _provider_layer(
                self.registry_provider,
                fallback_layer="narrative_registry",
            ),
            "stock_mappings": _provider_layer(
                self.mapping_provider,
                fallback_layer="stock_mappings",
            ),
            "mapping_evidence_packs": _local_file_layer(
                layer="mapping_evidence_packs",
                path=self.evidence_packs_path,
                note="Loaded from FNI local Mapping Evidence Pack prototype.",
            ),
            "candidate_intake_events": _local_file_layer(
                layer="candidate_intake_events",
                path=self.candidate_events_path,
                note="Loaded from FNI local Candidate Narrative Intake prototype.",
            ),
        }


def _provider_layer(provider: Any, *, fallback_layer: str) -> dict[str, Any]:
    get_provider_layer = getattr(provider, "get_provider_layer", None)
    if callable(get_provider_layer):
        return deepcopy(get_provider_layer())
    return {
        "layer": fallback_layer,
        "provider_name": "unknown",
        "provider_version": "unknown",
        "data_quality": "partial",
        "source_url": "unknown://provider-layer-unavailable",
        "is_mock": False,
        "note": "Provider does not expose layer provenance.",
    }


def _load_evidence_packs(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path, label="mapping evidence packs")
    if payload.get("version") != "mapping-evidence-pack-v0":
        raise ValueError("mapping evidence packs version must be mapping-evidence-pack-v0")
    if payload.get("trust_status") != "candidate_untrusted":
        raise ValueError("mapping evidence packs trust_status must be candidate_untrusted")
    if not isinstance(payload.get("packs"), list):
        raise ValueError("mapping evidence packs must include packs list")
    return deepcopy(payload)


def _load_candidate_events(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path, label="candidate narrative events")
    if payload.get("version") != "candidate-narrative-events-v1":
        raise ValueError(
            "candidate narrative events version must be candidate-narrative-events-v1"
        )
    if not isinstance(payload.get("events"), list):
        raise ValueError("candidate narrative events must include events list")
    return deepcopy(payload)


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FixtureNotFoundError(f"Missing {label}: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload


def _local_file_layer(*, layer: str, path: Path, note: str) -> dict[str, Any]:
    return {
        "layer": layer,
        "provider_name": LocalNarrativePrototypeProvider.provider_name,
        "provider_version": LocalNarrativePrototypeProvider.provider_version,
        "data_quality": "partial",
        "source_url": _local_source_url(path),
        "is_mock": False,
        "note": note,
    }


def _local_source_url(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        location = resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        path_hash = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        location = f"external/{path_hash}/{resolved.name}"
    content_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()[:12]
    return f"local-prototype://{quote(location, safe='/._-')}#sha256={content_hash}"

