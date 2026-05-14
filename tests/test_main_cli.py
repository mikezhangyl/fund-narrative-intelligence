import json

import pytest
from src import main as main_module
from src.config import FIXTURE_DIR
from src.errors import ProviderFetchError


def test_main_lists_fixtures(capsys):
    exit_code = main_module.main(["--list-fixtures"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "000001" in captured.out


def test_main_run_all_fixtures_prints_artifacts(tmp_path, capsys):
    exit_code = main_module.main(
        ["--run-all-fixtures", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Generated fixture artifacts:" in captured.out
    assert "000003" in captured.out


def test_main_requires_fund_code_when_no_batch_flag():
    with pytest.raises(SystemExit) as exc:
        main_module.main([])

    assert exc.value.code == 2


def test_main_previews_review_action_without_fund_code(tmp_path, capsys):
    action_path = tmp_path / "action.json"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_REJECT_TEST",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in CLI preview test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main_module.main(
        [
            "--preview-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    expected_path = tmp_path / "candidate_review_action_ACT_REJECT_TEST_preview.json"
    assert exit_code == 0
    assert "Review action preview:" in captured.out
    assert str(expected_path) in captured.out
    assert expected_path.exists()


def test_main_validates_review_action_preview_artifact(tmp_path, capsys):
    action_path = tmp_path / "action.json"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_REJECT_PREVIEW_VALIDATE",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in preview validation test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    main_module.main(
        [
            "--preview-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )
    preview_path = (
        tmp_path
        / "candidate_review_action_ACT_REJECT_PREVIEW_VALIDATE_preview.json"
    )

    exit_code = main_module.main(["--validate-review-preview", str(preview_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Review preview valid:" in captured.out
    assert str(preview_path) in captured.out


def test_main_validate_review_preview_rejects_malformed_file(tmp_path, capsys):
    preview_path = tmp_path / "bad-preview.json"
    preview_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main_module.main(["--validate-review-preview", str(preview_path)])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "review action preview missing required fields" in captured.err


def test_main_validates_review_queue_artifact(tmp_path, capsys):
    main_module.main(["--fund-code", "000001", "--output-dir", str(tmp_path)])
    queue_path = tmp_path / "fund_000001_review_queue.json"

    exit_code = main_module.main(["--validate-review-queue", str(queue_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Review queue valid:" in captured.out
    assert str(queue_path) in captured.out


def test_main_validate_review_queue_rejects_malformed_file(tmp_path, capsys):
    queue_path = tmp_path / "bad-review-queue.json"
    queue_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main_module.main(["--validate-review-queue", str(queue_path)])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "review queue artifact missing required fields" in captured.err


def test_main_validates_artifact_manifest(tmp_path, capsys):
    main_module.main(["--fund-code", "000001", "--output-dir", str(tmp_path)])
    manifest_path = tmp_path / "fund_000001_manifest.json"

    exit_code = main_module.main(["--validate-artifact-manifest", str(manifest_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Artifact manifest valid:" in captured.out
    assert str(manifest_path) in captured.out


def test_main_validate_artifact_manifest_rejects_malformed_file(tmp_path, capsys):
    manifest_path = tmp_path / "bad-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main_module.main(["--validate-artifact-manifest", str(manifest_path)])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "pipeline artifact manifest missing required fields" in captured.err


def test_main_validates_artifact_contract_directory(tmp_path, capsys):
    main_module.main(["--fund-code", "000001", "--output-dir", str(tmp_path)])
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.next.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_CONTRACTS_VALIDATE",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in artifact contract directory test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    main_module.main(
        [
            "--preview-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )
    main_module.main(
        [
            "--persist-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--registry-output",
            str(registry_output_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    exit_code = main_module.main(["--validate-artifact-contracts", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Artifact contracts valid:" in captured.out
    assert "manifests=1" in captured.out
    assert "source_tables=1" in captured.out
    assert "review_queues=1" in captured.out
    assert "review_previews=1" in captured.out
    assert "persistence_results=1" in captured.out


def test_main_validate_artifact_contracts_discovers_standalone_source_table(
    tmp_path,
    capsys,
):
    main_module.main(["--fund-code", "000001", "--output-dir", str(tmp_path)])
    (tmp_path / "fund_000001_manifest.json").unlink()
    (tmp_path / "fund_000001_review_queue.json").unlink()

    exit_code = main_module.main(["--validate-artifact-contracts", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "manifests=0" in captured.out
    assert "source_tables=1" in captured.out
    assert "review_queues=0" in captured.out


def test_main_validate_artifact_contracts_rejects_missing_manifest_file(
    tmp_path, capsys
):
    main_module.main(["--fund-code", "000001", "--output-dir", str(tmp_path)])
    (tmp_path / "fund_000001_raw.json").unlink()

    with pytest.raises(SystemExit) as exc:
        main_module.main(
            [
                "--validate-artifact-contracts",
                str(tmp_path / "fund_000001_manifest.json"),
            ]
        )

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "manifest artifact raw does not exist" in captured.err


def test_main_preview_review_action_uses_project_root_default_registry(
    tmp_path, monkeypatch, capsys
):
    action_path = tmp_path / "action.json"
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_DEFER_DEFAULT_REGISTRY",
                "candidate_narrative_id": "C_COMMUNICATION_POWER_INFRASTRUCTURE",
                "action": "defer",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Defer in default registry path test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    outside_repo = tmp_path / "outside"
    outside_repo.mkdir()
    monkeypatch.chdir(outside_repo)

    exit_code = main_module.main(
        [
            "--preview-review-action",
            str(action_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "candidate_review_action_ACT_DEFER_DEFAULT_REGISTRY_preview.json" in (
        captured.out
    )


def test_main_preview_review_action_rejects_missing_file(capsys):
    with pytest.raises(SystemExit) as exc:
        main_module.main(["--preview-review-action", "missing-action.json"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "does not exist" in captured.err


def test_main_persists_review_action_to_explicit_registry_output(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_REJECT_PERSIST_TEST",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in CLI persistence test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main_module.main(
        [
            "--persist-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--registry-output",
            str(registry_output_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    persisted_registry = json.loads(registry_output_path.read_text(encoding="utf-8"))
    audit_path = tmp_path / "candidate_review_action_ACT_REJECT_PERSIST_TEST_persistence.json"
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "Review action persisted:" in captured.out
    assert str(registry_output_path) in captured.out
    assert str(audit_path) in captured.out
    assert persisted_registry["candidate_narratives"][1]["status"] == "rejected"
    assert audit_payload["candidate_narrative_id"] == (
        "C_DOMESTIC_DATABASE_INFRASTRUCTURE"
    )


def test_main_persists_review_action_to_explicit_result_output(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    result_output_path = tmp_path / "audit" / "persistence.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_REJECT_PERSIST_EXPLICIT_RESULT",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in CLI explicit result test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main_module.main(
        [
            "--persist-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--registry-output",
            str(registry_output_path),
            "--persistence-result-output",
            str(result_output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert str(result_output_path) in captured.out
    assert result_output_path.exists()


def test_main_validates_persistence_result_artifact(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry.promoted.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_REJECT_VALIDATE_RESULT",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in CLI validation test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    main_module.main(
        [
            "--persist-review-action",
            str(action_path),
            "--registry-path",
            str(registry_path),
            "--registry-output",
            str(registry_output_path),
            "--output-dir",
            str(tmp_path),
        ]
    )
    result_path = (
        tmp_path
        / "candidate_review_action_ACT_REJECT_VALIDATE_RESULT_persistence.json"
    )

    exit_code = main_module.main(["--validate-persistence-result", str(result_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Persistence result valid:" in captured.out
    assert str(result_path) in captured.out


def test_main_validate_persistence_result_rejects_malformed_file(tmp_path, capsys):
    result_path = tmp_path / "bad-result.json"
    result_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main_module.main(["--validate-persistence-result", str(result_path)])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "review action persistence result missing required fields" in captured.err


def test_main_persist_review_action_rejects_directory_output(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    action_path = tmp_path / "action.json"
    registry_output_path = tmp_path / "registry-output-dir"
    registry_output_path.mkdir()
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    action_path.write_text(
        json.dumps(
            {
                "action_id": "ACT_REJECT_DIRECTORY_TEST",
                "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
                "action": "reject",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-05-14T11:00:00+00:00",
                "review_note": "Reject in CLI directory test.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        main_module.main(
            [
                "--persist-review-action",
                str(action_path),
                "--registry-path",
                str(registry_path),
                "--registry-output",
                str(registry_output_path),
            ]
        )

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "must not be a directory" in captured.err


def test_main_persist_review_action_requires_registry_output(tmp_path):
    action_path = tmp_path / "action.json"
    action_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main_module.main(["--persist-review-action", str(action_path)])

    assert exc.value.code == 2


def test_main_returns_controlled_error_for_missing_fixture(tmp_path, capsys):
    exit_code = main_module.main(
        ["--fund-code", "999999", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No mock fixture found for fund code 999999" in captured.err


def test_main_rejects_invalid_fund_code(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main_module.main(["--fund-code", "ABC", "--output-dir", str(tmp_path)])

    assert exc.value.code == 2


def test_main_run_real_smoke_returns_status(monkeypatch, tmp_path, capsys):
    def fake_run_real_fund_smoke(output_dir):
        assert output_dir == str(tmp_path)
        return {
            "status": "passed",
            "funds": [
                {
                    "fund_code": "161725",
                    "scenario": "baijiu_consumption",
                    "primary_narrative": "Premium Baijiu Consumption",
                    "stage": "diverging",
                    "coverage_ratio": 1.0,
                    "mapping_precision_flag_count": 2,
                    "excluded_mapping_candidate_count": 1,
                    "candidate_narrative_count": 1,
                    "candidate_review_queue_item_count": 1,
                }
            ],
        }

    monkeypatch.setattr(
        main_module, "run_real_fund_smoke", fake_run_real_fund_smoke
    )

    exit_code = main_module.main(
        ["--run-real-smoke", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "status=passed" in captured.out
    assert "coverage=100%" in captured.out
    assert "precision_flags=2" in captured.out
    assert "excluded_candidates=1" in captured.out
    assert "candidate_narratives=1" in captured.out
    assert "review_queue=1" in captured.out


def test_main_run_real_smoke_returns_nonzero_for_failed_summary(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        main_module,
        "run_real_fund_smoke",
        lambda output_dir: {"status": "failed", "funds": []},
    )

    exit_code = main_module.main(
        ["--run-real-smoke", "--output-dir", str(tmp_path)]
    )

    assert exit_code == 1


def test_main_run_real_smoke_handles_controlled_error(monkeypatch, capsys):
    def failing_run_real_fund_smoke(output_dir):
        raise ProviderFetchError("provider unavailable")

    monkeypatch.setattr(
        main_module, "run_real_fund_smoke", failing_run_real_fund_smoke
    )

    exit_code = main_module.main(["--run-real-smoke"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "provider unavailable" in captured.err


def test_main_run_announcement_smoke_returns_status(monkeypatch, tmp_path, capsys):
    def fake_run_announcement_evidence_smoke(output_dir):
        assert output_dir == str(tmp_path)
        return {
            "status": "passed",
            "cases": [
                {
                    "fund_code": "161725",
                    "scenario": "baijiu_cninfo_metadata",
                    "announcement_count": 56,
                    "announcement_evidence_count": 56,
                    "data_source_notice_required": True,
                    "effective_data_quality": "partial",
                }
            ],
        }

    monkeypatch.setattr(
        main_module,
        "run_announcement_evidence_smoke",
        fake_run_announcement_evidence_smoke,
    )

    exit_code = main_module.main(
        ["--run-announcement-smoke", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Announcement evidence smoke summary:" in captured.out
    assert "status=passed" in captured.out
    assert "161725 baijiu_cninfo_metadata announcements=56 evidence=56" in captured.out


def test_main_run_announcement_smoke_returns_nonzero_for_failed_summary(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        main_module,
        "run_announcement_evidence_smoke",
        lambda output_dir: {"status": "failed", "cases": []},
    )

    exit_code = main_module.main(
        ["--run-announcement-smoke", "--output-dir", str(tmp_path)]
    )

    assert exit_code == 1
