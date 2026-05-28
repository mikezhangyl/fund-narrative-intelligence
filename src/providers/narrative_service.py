from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

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
class NarrativeServiceProvider:
    base_url: str
    timeout_seconds: float = 10.0

    provider_name = "narrative-service-provider"
    provider_version = "narrative-service-provider-v1"
    source = "narrative_service"

    def get_snapshot(self) -> dict[str, Any]:
        registry_envelope = self._get("/api/v1/narratives/registry")
        mappings_envelope = self._get("/api/v1/narratives/mappings")
        evidence_pack_envelope = self._get("/api/v1/narratives/evidence-packs")
        candidates_envelope = self._get("/api/v1/narratives/candidates")
        trust_audit_envelope = self._get("/api/v1/narratives/trust-audits/latest")
        review_queue_envelope = self._get("/api/v1/narratives/review-queue")
        registry = _extract_registry(registry_envelope["data"])
        mappings = _extract_mappings(mappings_envelope["data"])
        return {
            "status": "available",
            "source": self.source,
            "provider": str(registry_envelope.get("provider") or self.provider_name),
            "provider_version": str(
                registry_envelope.get("provider_version") or self.provider_version
            ),
            "narrative_registry": deepcopy(registry),
            "stock_narrative_mappings": deepcopy(mappings),
            "mapping_evidence_packs": deepcopy(evidence_pack_envelope["data"]),
            "candidate_narratives": deepcopy(candidates_envelope["data"]),
            "trust_audit": deepcopy(trust_audit_envelope["data"]),
            "review_queue": deepcopy(review_queue_envelope["data"]),
            "provider_layers": {
                "narrative_registry": _service_layer(
                    layer="narrative_registry",
                    envelope=registry_envelope,
                    url=self._url("/api/v1/narratives/registry"),
                ),
                "stock_mappings": _service_layer(
                    layer="stock_mappings",
                    envelope=mappings_envelope,
                    url=self._url("/api/v1/narratives/mappings"),
                ),
                "mapping_evidence_packs": _service_layer(
                    layer="mapping_evidence_packs",
                    envelope=evidence_pack_envelope,
                    url=self._url("/api/v1/narratives/evidence-packs"),
                ),
            },
            "warnings": _envelope_warnings(
                [
                    registry_envelope,
                    mappings_envelope,
                    evidence_pack_envelope,
                    candidates_envelope,
                    trust_audit_envelope,
                    review_queue_envelope,
                ]
            ),
            "diagnostics": {
                "local_fallback": False,
                "service_ready": True,
                "registry_count": len(registry.get("narratives", [])),
                "candidate_registry_count": len(
                    registry.get("candidate_narratives", [])
                ),
                "stock_mapping_count": len(mappings),
            },
        }

    def get_report_inputs(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        snapshot = self.get_snapshot()
        return (
            deepcopy(snapshot["narrative_registry"]),
            deepcopy(snapshot["stock_narrative_mappings"]),
        )

    def _get(self, path: str) -> dict[str, Any]:
        return _require_envelope(
            _request_json(
                method="GET",
                url=self._url(path),
                payload=None,
                timeout_seconds=self.timeout_seconds,
            ),
            path=path,
        )

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url.rstrip('/')}/", path.lstrip("/"))


@dataclass(frozen=True)
class FallbackNarrativeDataProvider:
    primary: NarrativeDataProvider
    fallback: NarrativeDataProvider = field(
        default_factory=lambda: LocalNarrativePrototypeProvider()
    )

    def get_snapshot(self) -> dict[str, Any]:
        try:
            return self.primary.get_snapshot()
        except Exception as exc:
            snapshot = self.fallback.get_snapshot()
            warning = {
                "code": "NARRATIVE_SERVICE_FALLBACK",
                "message": f"Narrative service unavailable; using local fallback: {exc}",
            }
            return {
                **snapshot,
                "warnings": [warning, *list(snapshot.get("warnings", []))],
                "diagnostics": {
                    **dict(snapshot.get("diagnostics", {})),
                    "service_ready": False,
                    "service_failure_reason": str(exc),
                },
            }

    def get_report_inputs(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        snapshot = self.get_snapshot()
        return (
            deepcopy(snapshot["narrative_registry"]),
            deepcopy(snapshot["stock_narrative_mappings"]),
        )


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


def build_narrative_data_provider(
    *,
    base_url: str | None = None,
    timeout_seconds: float = 10.0,
) -> NarrativeDataProvider:
    resolved_base_url = (base_url if base_url is not None else os.environ.get(
        "NARRATIVE_SERVICE_URL",
        "",
    )).strip()
    local_provider = LocalNarrativePrototypeProvider()
    if not resolved_base_url:
        return local_provider
    return FallbackNarrativeDataProvider(
        primary=NarrativeServiceProvider(
            base_url=resolved_base_url,
            timeout_seconds=timeout_seconds,
        ),
        fallback=local_provider,
    )


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


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    if not isinstance(response_payload, dict):
        raise ValueError("narrative service response must be a JSON object")
    return response_payload


def _require_envelope(payload: dict[str, Any], *, path: str) -> dict[str, Any]:
    required = {
        "status",
        "source",
        "provider",
        "provider_version",
        "data",
        "warnings",
        "trust_metadata",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"{path} response missing envelope fields: {', '.join(missing)}")
    if not isinstance(payload.get("warnings"), list):
        raise ValueError(f"{path} response warnings must be a list")
    if not isinstance(payload.get("trust_metadata"), dict):
        raise ValueError(f"{path} response trust_metadata must be an object")
    return deepcopy(payload)


def _extract_registry(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("registry data must be an object")
    nested = data.get("narrative_registry")
    if isinstance(nested, dict):
        return deepcopy(nested)
    return deepcopy(data)


def _extract_mappings(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return deepcopy(data)
    if isinstance(data, dict):
        for field in ("mappings", "stock_narrative_mappings"):
            rows = data.get(field)
            if isinstance(rows, list):
                return deepcopy(rows)
    raise ValueError("mappings data must be a list or object with mappings list")


def _service_layer(*, layer: str, envelope: dict[str, Any], url: str) -> dict[str, Any]:
    return {
        "layer": layer,
        "provider_name": str(envelope.get("provider") or "narrative-service"),
        "provider_version": str(envelope.get("provider_version") or ""),
        "data_quality": _service_data_quality(envelope),
        "source_url": url,
        "is_mock": False,
        "note": "Loaded from configured Narrative Service endpoint.",
        "trust_metadata": deepcopy(envelope.get("trust_metadata", {})),
    }


def _service_data_quality(envelope: dict[str, Any]) -> str:
    status = str(envelope.get("status") or "")
    if status in {"available", "completed", "ok"}:
        return "fresh"
    if status in {"partial", "degraded"}:
        return "partial"
    return "unavailable"


def _envelope_warnings(envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for envelope in envelopes:
        for warning in envelope.get("warnings", []):
            if isinstance(warning, dict):
                warnings.append(deepcopy(warning))
    return warnings


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
