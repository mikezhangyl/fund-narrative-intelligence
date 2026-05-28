from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "data" / "fixtures"
REGISTRY_DIR = PROJECT_ROOT / "data" / "registry"
DEFAULT_REVIEWED_REGISTRY_PATH = REGISTRY_DIR / "narrative_registry.reviewed.json"
DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH = (
    REGISTRY_DIR / "stock_narrative_mappings.reviewed.json"
)
DEFAULT_MAPPING_EVIDENCE_PACKS_PATH = REGISTRY_DIR / "mapping_evidence_packs.v0.json"
DEFAULT_CANDIDATE_NARRATIVE_EVENTS_PATH = (
    FIXTURE_DIR / "candidate_narrative_events.v1.json"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"

VERSION_DEFAULTS = {
    "provider_set_version": "mock-v1",
    "narrative_registry_version": "registry-v1",
    "signal_schema_version": "signals-v1",
    "scoring_model_version": "scoring-v1",
    "report_template_version": "report-v1",
}

DATA_QUALITY_CONFIDENCE = {
    "fresh": 1.0,
    "mock": 0.5,
    "partial": 0.75,
    "stale": 0.6,
    "unavailable": 0.0,
}
