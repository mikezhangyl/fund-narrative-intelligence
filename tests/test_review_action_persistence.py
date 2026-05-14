import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from src.modules.narrative_review import persistence as persistence_module
from src.modules.narrative_review.persistence import persist_review_action_registry
from src.validation import validate_registry_payload

FIXTURE_DIR = Path("data/fixtures")


def _registry_text() -> str:
    return (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8")


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


def test_persist_review_action_writes_new_registry_without_mutating_source(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "registry.promoted.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )
    before = registry_path.read_text(encoding="utf-8")

    result = persist_review_action_registry(
        registry_path=registry_path,
        action_path=action_path,
        registry_output_path=output_path,
        result_output_dir=tmp_path,
    )

    assert registry_path.read_text(encoding="utf-8") == before
    assert result["version"] == "review-action-persistence-result-v1"
    assert result["status"] == "persisted"
    assert result["registry_overwritten"] is False
    assert result["registry_delta"]["active_narrative_ids_added"] == [
        "N_CONSUMER_ELECTRONICS_GLOBALIZATION"
    ]
    persisted_registry = json.loads(output_path.read_text(encoding="utf-8"))
    validate_registry_payload(persisted_registry)
    assert persisted_registry["narratives"][-1]["narrative_id"] == (
        "N_CONSUMER_ELECTRONICS_GLOBALIZATION"
    )


def test_persist_review_action_requires_audit_output_location(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "registry.promoted.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="persistence result output"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=output_path,
        )


def test_persist_review_action_writes_persistence_result_artifact(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    result_output_path = tmp_path / "audit" / "result.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = persist_review_action_registry(
        registry_path=registry_path,
        action_path=action_path,
        registry_output_path=registry_output_path,
        result_output_path=result_output_path,
    )

    result_artifact = json.loads(result_output_path.read_text(encoding="utf-8"))
    assert result["persistence_result_path"] == str(result_output_path.resolve())
    assert result_artifact == result
    assert result_artifact["version"] == "review-action-persistence-result-v1"
    assert result_artifact["overwrite_policy"] == {
        "allow_registry_overwrite": False,
        "allow_output_overwrite": False,
        "allow_result_overwrite": False,
    }
    assert result_artifact["registry_delta"]["active_narrative_ids_added"] == [
        "N_CONSUMER_ELECTRONICS_GLOBALIZATION"
    ]


def test_persist_review_action_rejects_result_artifact_source_overwrite(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    for forbidden_path in (registry_path, action_path, registry_output_path):
        with pytest.raises(ValueError, match="persistence result output must not"):
            persist_review_action_registry(
                registry_path=registry_path,
                action_path=action_path,
                registry_output_path=registry_output_path,
                result_output_path=forbidden_path,
                allow_registry_overwrite=True,
                allow_output_overwrite=True,
                allow_result_overwrite=True,
            )
        assert not registry_output_path.exists()


def test_persist_review_action_rejects_case_alias_result_output(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "Registry.Next.json"
    result_output_path = tmp_path / "registry.next.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="persistence result output must not"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=registry_output_path,
            result_output_path=result_output_path,
        )
    assert not registry_output_path.exists()
    assert not result_output_path.exists()


def test_persist_review_action_rejects_existing_result_artifact_by_default(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    result_output_path = tmp_path / "result.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )
    result_output_path.write_text("do not replace", encoding="utf-8")

    with pytest.raises(ValueError, match="persistence result output already exists"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=registry_output_path,
            result_output_path=result_output_path,
        )
    assert result_output_path.read_text(encoding="utf-8") == "do not replace"


def test_persist_review_action_rejects_in_place_without_explicit_allow(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires allow_registry_overwrite"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=registry_path,
        )


def test_persist_review_action_allows_explicit_in_place_overwrite(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = persist_review_action_registry(
        registry_path=registry_path,
        action_path=action_path,
        registry_output_path=registry_path,
        result_output_dir=tmp_path / "audit",
        allow_registry_overwrite=True,
    )

    assert result["registry_overwritten"] is True
    persisted_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert persisted_registry["candidate_narratives"][0]["status"] == "promoted"


def test_persist_review_action_rejects_existing_output_without_explicit_allow(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "registry.next.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )
    output_path.write_text("do not replace", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=output_path,
        )
    assert output_path.read_text(encoding="utf-8") == "do not replace"


def test_persist_review_action_allows_explicit_existing_output_overwrite(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "registry.next.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )
    output_path.write_text("replace me", encoding="utf-8")

    result = persist_review_action_registry(
        registry_path=registry_path,
        action_path=action_path,
        registry_output_path=output_path,
        result_output_dir=tmp_path / "audit",
        allow_output_overwrite=True,
    )

    assert result["registry_overwritten"] is False
    assert json.loads(output_path.read_text(encoding="utf-8"))["narratives"][-1][
        "narrative_id"
    ] == "N_CONSUMER_ELECTRONICS_GLOBALIZATION"


def test_persist_review_action_rejects_directory_output(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "output-dir"
    output_path.mkdir()
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must not be a directory"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=output_path,
        )


def test_persist_review_action_rejects_temporary_path_collision(tmp_path):
    registry_path = tmp_path / "registry.json"
    output_path = tmp_path / "registry.next.json"
    action_path = tmp_path / f".{output_path.name}.tmp"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="temporary output path must not collide"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=output_path,
        )
    assert action_path.exists()


def test_persist_review_action_uses_unique_temp_files_for_parallel_writes(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    output_path = tmp_path / "registry.next.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    def persist_once() -> dict:
        return persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=output_path,
            result_output_dir=tmp_path / "audit",
            allow_output_overwrite=True,
            allow_result_overwrite=True,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: persist_once(), range(2)))

    assert [result["status"] for result in results] == ["persisted", "persisted"]
    assert json.loads(output_path.read_text(encoding="utf-8"))["narratives"][-1][
        "narrative_id"
    ] == "N_CONSUMER_ELECTRONICS_GLOBALIZATION"


def test_persist_review_action_rejects_action_input_overwrite(tmp_path):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must not overwrite action input"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=action_path,
            allow_registry_overwrite=True,
        )


def test_persist_review_action_rolls_back_registry_when_audit_write_fails(
    tmp_path, monkeypatch
):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    registry_path.write_text(_registry_text(), encoding="utf-8")
    action_path.write_text(
        json.dumps(_approve_action(), ensure_ascii=False),
        encoding="utf-8",
    )
    real_writer = persistence_module._write_json_atomically
    calls: list[Path] = []

    def flaky_writer(payload: dict, output_path: Path) -> None:
        calls.append(output_path)
        if len(calls) == 2:
            raise OSError("audit write failed")
        real_writer(payload, output_path)

    monkeypatch.setattr(
        persistence_module,
        "_write_json_atomically",
        flaky_writer,
    )

    with pytest.raises(OSError, match="audit write failed"):
        persist_review_action_registry(
            registry_path=registry_path,
            action_path=action_path,
            registry_output_path=registry_output_path,
            result_output_dir=tmp_path,
        )

    assert not registry_output_path.exists()
