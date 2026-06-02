from __future__ import annotations

import json
import zipfile

from scripts import run_backup_restore_archive
from src.scanners.backup_restore_archive import (
    build_backup_restore_archive_manifest,
    render_backup_restore_archive_html,
)


def test_backup_archive_manifest_excludes_secrets_and_preserves_restore_contract(tmp_path):
    workspace = _write(tmp_path / "outputs/product_shell/round8-current/workspace_state.json", "{}")
    handoff = _write(tmp_path / "outputs/collaboration_handoff/current/collaboration_handoff_bundle.json", '{"version":"collaboration-handoff-bundle-v1"}')
    secret = _write(tmp_path / ".local.env", "API_TOKEN=super-secret")

    manifest = build_backup_restore_archive_manifest(
        project_root=tmp_path,
        include_paths=[workspace, handoff, secret],
        release_metadata={"release_id": "r12-local", "version": "2026.06.02"},
        generated_at="2026-06-02T08:30:00+08:00",
    )

    assert manifest["version"] == "backup-restore-archive-v1"
    assert manifest["summary"] == {
        "included_file_count": 2,
        "excluded_file_count": 1,
        "warning_count": 0,
    }
    assert manifest["restore_contract"] == {
        "compatibility_version": "backup-restore-archive-v1",
        "restore_validation_required": True,
        "rollback_supported": True,
        "current_state_overwrite_allowed_without_validation": False,
    }
    assert [item["path"] for item in manifest["included_files"]] == [
        "outputs/collaboration_handoff/current/collaboration_handoff_bundle.json",
        "outputs/product_shell/round8-current/workspace_state.json",
    ]
    assert manifest["excluded_files"][0]["reason"] == "secret_or_local_environment_path"
    assert "super-secret" not in json.dumps(manifest, ensure_ascii=False)


def test_backup_archive_html_is_chinese_and_lists_integrity_manifest(tmp_path):
    workspace = _write(tmp_path / "outputs/product_shell/round8-current/workspace_state.json", "{}")
    html = render_backup_restore_archive_html(
        build_backup_restore_archive_manifest(
            project_root=tmp_path,
            include_paths=[workspace],
            release_metadata={"release_id": "r12-local"},
        )
    )

    assert "<h1>备份恢复与便携发布归档</h1>" in html
    assert "完整性校验" in html
    assert "workspace_state.json" in html


def test_backup_archive_cli_writes_manifest_html_and_zip(tmp_path):
    workspace = _write(tmp_path / "outputs/product_shell/round8-current/workspace_state.json", "{}")
    handoff = _write(tmp_path / "outputs/collaboration_handoff/current/collaboration_handoff_bundle.json", "{}")
    input_path = tmp_path / "archive_input.json"
    output_dir = tmp_path / "archive"
    input_path.write_text(
        json.dumps(
            {
                "include_paths": [str(workspace), str(handoff)],
                "release_metadata": {"release_id": "r12-local"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = run_backup_restore_archive.main(
        ["--input", str(input_path), "--project-root", str(tmp_path), "--output-dir", str(output_dir)]
    )

    manifest = json.loads((output_dir / "backup_restore_archive_manifest.json").read_text())
    zip_path = output_dir / "backup_restore_archive.zip"

    assert exit_code == 0
    assert zip_path.exists()
    assert manifest["summary"]["included_file_count"] == 2
    assert manifest["archive"]["zip_path"] == str(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == [
            "outputs/collaboration_handoff/current/collaboration_handoff_bundle.json",
            "outputs/product_shell/round8-current/workspace_state.json",
        ]
    assert "<h1>备份恢复与便携发布归档</h1>" in (
        output_dir / "backup_restore_archive.html"
    ).read_text()


def _write(path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
