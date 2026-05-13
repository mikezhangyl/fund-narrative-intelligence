import json
from pathlib import Path

from src.modules.signal_service.scoring import score_narrative_state

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "data" / "fixtures"

EXPECTED_REAL_SMOKE_STAGES = {
    "N_BAIJIU_CONSUMPTION": "diverging",
    "N_SEMI_CAPEX": "strengthening",
    "N_HEALTHCARE_INNOVATION": "diverging",
    "N_NEW_ENERGY_EQUIPMENT": "weakening",
    "N_DEFENSE_AEROSPACE": "strengthening",
    "N_REAL_ESTATE_STABILIZATION": "weakening",
}


def test_real_smoke_signal_fixtures_produce_differentiated_stages():
    signal_events = _load_fixture("signal_events.json")["signal_events"]
    evidence = _load_fixture("evidence.json")["evidence"]

    stages = {
        narrative_id: score_narrative_state(
            narrative_id=narrative_id,
            signal_events=signal_events,
            mapping_confidence=0.7,
            evidence_count=sum(
                1 for item in evidence if item["narrative_id"] == narrative_id
            ),
            as_of_date="2026-05-13",
            data_quality="fresh",
        )["stage"]
        for narrative_id in EXPECTED_REAL_SMOKE_STAGES
    }

    assert stages == EXPECTED_REAL_SMOKE_STAGES
    assert len(set(stages.values())) >= 3


def _load_fixture(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))
