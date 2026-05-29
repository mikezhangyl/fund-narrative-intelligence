from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[2]
FNI_ROOT = SERVICE_ROOT.parents[1]


@dataclass(frozen=True)
class ServiceConfig:
    registry_path: Path = FNI_ROOT / "data" / "registry" / "narrative_registry.reviewed.json"
    mappings_path: Path = (
        FNI_ROOT / "data" / "registry" / "stock_narrative_mappings.reviewed.json"
    )
    evidence_packs_path: Path = (
        FNI_ROOT / "data" / "registry" / "mapping_evidence_packs.v0.json"
    )
    candidate_events_path: Path = (
        FNI_ROOT / "data" / "fixtures" / "candidate_narrative_events.v1.json"
    )
    intake_ledger_path: Path = (
        SERVICE_ROOT / "data" / "runtime" / "candidate_intake_events.json"
    )
    review_actions_path: Path = SERVICE_ROOT / "data" / "runtime" / "review_actions.json"
    promotion_decisions_path: Path = (
        SERVICE_ROOT / "data" / "runtime" / "promotion_decisions.json"
    )
    market_confirmation_path: Path = (
        SERVICE_ROOT / "data" / "runtime" / "radar_market_confirmation.json"
    )
    job_definitions_path: Path = (
        SERVICE_ROOT / "data" / "runtime" / "job_definitions.json"
    )
    job_runs_path: Path = SERVICE_ROOT / "data" / "runtime" / "job_runs.json"
    provider_name: str = "stock-narrative-service"
    provider_version: str = "v0"
