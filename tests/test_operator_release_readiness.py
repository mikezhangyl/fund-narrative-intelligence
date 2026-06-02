from __future__ import annotations

import json

from scripts import run_operator_release_readiness
from src.scanners.operator_release_readiness import (
    build_operator_release_readiness,
    render_operator_release_readiness_html,
)


def test_release_readiness_contract_contains_operator_handoff_sections():
    readiness = build_operator_release_readiness(
        release_metadata=_release_metadata(),
        generated_at="2026-06-02T09:00:00+08:00",
    )

    assert readiness["version"] == "operator-release-readiness-v1"
    assert readiness["summary"] == {
        "release_note_count": 3,
        "verification_command_count": 4,
        "known_limitation_count": 3,
        "support_runbook_count": 4,
    }
    assert readiness["contract"] == {
        "external_identity_provider_required": False,
        "hosted_saas_deployment_required": False,
        "local_deterministic_mode_preserved": True,
        "breaking_change_disclosure_required": True,
    }
    assert readiness["compatibility_table"][0]["component"] == "product_shell"
    assert readiness["verification_commands"][0]["command"] == "uv run pytest"
    assert readiness["known_limitations"][0]["severity"] == "expected"
    assert "public launch" not in json.dumps(readiness, ensure_ascii=False).casefold()


def test_release_readiness_html_is_chinese_and_lists_support_runbooks():
    html = render_operator_release_readiness_html(
        build_operator_release_readiness(release_metadata=_release_metadata())
    )

    assert "<h1>操作员上线指引与发布说明</h1>" in html
    assert "验证命令" in html
    assert "support-backup-restore" in html
    assert "已知限制" in html


def test_release_readiness_cli_writes_json_html(tmp_path):
    input_path = tmp_path / "release.json"
    output_dir = tmp_path / "release"
    input_path.write_text(json.dumps(_release_metadata(), ensure_ascii=False), encoding="utf-8")

    exit_code = run_operator_release_readiness.main(
        ["--input", str(input_path), "--output-dir", str(output_dir)]
    )

    payload = json.loads((output_dir / "operator_release_readiness.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["support_runbook_count"] == 4
    assert "<h1>操作员上线指引与发布说明</h1>" in (
        output_dir / "operator_release_readiness.html"
    ).read_text()


def _release_metadata() -> dict[str, object]:
    return {
        "release_id": "r12-collaboration-readiness-local",
        "version": "2026.06.02",
        "source_artifacts": [
            "outputs/collaboration_handoff/current/collaboration_handoff_bundle.json",
            "outputs/backup_restore_archive/current/backup_restore_archive_manifest.json",
        ],
    }
