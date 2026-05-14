import copy
import json
from pathlib import Path

import pytest
from src.errors import ProviderContractError
from src.modules.narrative_review.preview import (
    build_review_action_preview,
    write_review_action_preview,
)

FIXTURE_DIR = Path("data/fixtures")


def _registry_payload() -> dict:
    return json.loads((FIXTURE_DIR / "narrative_registry.json").read_text())


def _approve_action() -> dict:
    return {
        "action_id": "ACT_APPROVE_CONSUMER_ELECTRONICS",
        "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "action": "approve",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T10:00:00+00:00",
        "review_note": "Promote as a separate technology hardware theme.",
        "promotion": {
            "narrative_id": "N_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "parent_id": None,
            "level": 2,
            "aliases": ["consumer electronics exports", "device globalization"],
            "related_terms": ["消费电子", "终端设备", "海外手机", "传音控股"],
        },
    }


def test_build_review_action_preview_applies_action_without_mutating_registry():
    registry = _registry_payload()
    original = copy.deepcopy(registry)

    preview = build_review_action_preview(registry, _approve_action())

    assert registry == original
    assert preview["version"] == "candidate-review-action-preview-v1"
    assert preview["status"] == "previewed"
    assert preview["source_registry_mutated"] is False
    assert preview["action"]["action_id"] == "ACT_APPROVE_CONSUMER_ELECTRONICS"
    assert preview["summary"] == {
        "action": "approve",
        "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "candidate_status_after": "promoted",
        "human_review_status_after": "approved",
        "active_narrative_count_before": len(registry["narratives"]),
        "active_narrative_count_after": len(registry["narratives"]) + 1,
        "promotion_target_id": "N_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "source_registry_written": False,
        "requires_explicit_persistence_step": True,
    }
    assert preview["result_registry"]["narratives"][-1]["narrative_id"] == (
        "N_CONSUMER_ELECTRONICS_GLOBALIZATION"
    )


def test_build_review_action_preview_summarizes_reject_without_promotion():
    registry = _registry_payload()
    action = {
        "action_id": "ACT_REJECT_DATABASE_INFRA",
        "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
        "action": "reject",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T11:00:00+00:00",
        "review_note": "Too narrow for the current taxonomy.",
    }

    preview = build_review_action_preview(registry, action)

    assert preview["summary"]["candidate_status_after"] == "rejected"
    assert preview["summary"]["human_review_status_after"] == "rejected"
    assert preview["summary"]["active_narrative_count_after"] == len(
        registry["narratives"]
    )
    assert preview["summary"]["promotion_target_id"] is None


def test_write_review_action_preview_uses_default_filename_and_preserves_registry(
    tmp_path,
):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_path.write_text(
        json.dumps(_registry_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )
    before = registry_path.read_text(encoding="utf-8")

    output_path = write_review_action_preview(
        registry_path=registry_path,
        action_path=action_path,
        output_dir=tmp_path,
    )

    assert output_path == (
        tmp_path / "candidate_review_action_ACT_APPROVE_CONSUMER_ELECTRONICS_preview.json"
    )
    assert registry_path.read_text(encoding="utf-8") == before
    preview = json.loads(output_path.read_text(encoding="utf-8"))
    assert preview["summary"]["source_registry_written"] is False
    assert preview["summary"]["requires_explicit_persistence_step"] is True


def test_write_review_action_preview_supports_explicit_output_path(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "nested" / "preview.json"
    registry_path.write_text(
        json.dumps(_registry_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    written_path = write_review_action_preview(
        registry_path=registry_path,
        action_path=action_path,
        output_dir=tmp_path,
        output_path=output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_write_review_action_preview_rejects_source_file_overwrite(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_path.write_text(
        json.dumps(_registry_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must not overwrite registry or action input"):
        write_review_action_preview(
            registry_path=registry_path,
            action_path=action_path,
            output_dir=tmp_path,
            output_path=registry_path,
        )
    with pytest.raises(ValueError, match="must not overwrite registry or action input"):
        write_review_action_preview(
            registry_path=registry_path,
            action_path=action_path,
            output_dir=tmp_path,
            output_path=action_path,
        )


def test_write_review_action_preview_rejects_output_outside_output_dir(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(
        json.dumps(_registry_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must stay inside output_dir"):
        write_review_action_preview(
            registry_path=registry_path,
            action_path=action_path,
            output_dir=output_dir,
            output_path=tmp_path / "preview.json",
        )


def test_write_review_action_preview_reports_missing_input_as_validation_error(
    tmp_path,
):
    with pytest.raises(ValueError, match="does not exist"):
        write_review_action_preview(
            registry_path=tmp_path / "missing-registry.json",
            action_path=tmp_path / "missing-action.json",
            output_dir=tmp_path,
        )


def test_build_review_action_preview_rejects_invalid_action_payload():
    with pytest.raises(ProviderContractError, match="review action missing"):
        build_review_action_preview(_registry_payload(), {"action": "reject"})
