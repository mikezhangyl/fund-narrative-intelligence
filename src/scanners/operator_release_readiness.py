from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_operator_release_readiness(
    *,
    release_metadata: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    release_notes = _release_notes(release_metadata)
    verification_commands = _verification_commands()
    known_limitations = _known_limitations()
    support_runbooks = _support_runbooks()
    return {
        "version": "operator-release-readiness-v1",
        "generated_at": generated_at or _utc_now(),
        "release_metadata": release_metadata,
        "summary": {
            "release_note_count": len(release_notes),
            "verification_command_count": len(verification_commands),
            "known_limitation_count": len(known_limitations),
            "support_runbook_count": len(support_runbooks),
        },
        "contract": {
            "external_identity_provider_required": False,
            "hosted_saas_deployment_required": False,
            "local_deterministic_mode_preserved": True,
            "breaking_change_disclosure_required": True,
        },
        "release_notes": release_notes,
        "compatibility_table": [
            {"component": "product_shell", "version": "round8-current", "compatibility": "compatible"},
            {"component": "collaboration_handoff", "version": "collaboration-handoff-bundle-v1", "compatibility": "new_non_breaking"},
            {"component": "backup_restore_archive", "version": "backup-restore-archive-v1", "compatibility": "new_non_breaking"},
        ],
        "verification_commands": verification_commands,
        "known_limitations": known_limitations,
        "support_runbooks": support_runbooks,
    }


def render_operator_release_readiness_html(readiness: dict[str, Any]) -> str:
    summary = _mapping(readiness.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>操作员上线指引与发布说明</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>操作员上线指引与发布说明</h1>",
            '<section class="summary">',
            _html_kv("发布说明", summary.get("release_note_count", 0)),
            _html_kv("验证命令", summary.get("verification_command_count", 0)),
            _html_kv("已知限制", summary.get("known_limitation_count", 0)),
            _html_kv("支持 runbook", summary.get("support_runbook_count", 0)),
            "</section>",
            _commands_table(_list(readiness.get("verification_commands"))),
            _limitations_table(_list(readiness.get("known_limitations"))),
            _runbooks_table(_list(readiness.get("support_runbooks"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _release_notes(release_metadata: dict[str, Any]) -> list[dict[str, str]]:
    release_id = str(release_metadata.get("release_id") or "local-release")
    return [
        {
            "note_id": "release-collaboration-handoff",
            "change_type": "non_breaking",
            "description": f"{release_id} adds collaboration handoff bundle artifacts.",
        },
        {
            "note_id": "release-backup-restore",
            "change_type": "non_breaking",
            "description": "Adds portable backup archive manifest, HTML report, and zip artifact.",
        },
        {
            "note_id": "release-local-mode",
            "change_type": "no_breaking_change",
            "description": "Local deterministic mode remains the default operating mode.",
        },
    ]


def _verification_commands() -> list[dict[str, str]]:
    return [
        {"command": "uv run pytest", "purpose": "full Python regression suite"},
        {"command": "uv run ruff check .", "purpose": "lint and import hygiene"},
        {"command": "uv run python scripts/run_collaboration_handoff_bundle.py", "purpose": "regenerate handoff artifacts"},
        {"command": "uv run python scripts/run_backup_restore_archive.py", "purpose": "regenerate backup archive artifacts"},
    ]


def _known_limitations() -> list[dict[str, str]]:
    return [
        {"limitation_id": "local-role-placeholders", "severity": "expected", "description": "Roles are local placeholders, not external identity enforcement."},
        {"limitation_id": "selected-archive-scope", "severity": "expected", "description": "Backup archive contains selected readiness artifacts, not every historical output."},
        {"limitation_id": "manual-restore", "severity": "expected", "description": "Restore overwrite is documented as a validation contract and remains manual."},
    ]


def _support_runbooks() -> list[dict[str, str]]:
    return [
        {"runbook_id": "support-handoff-review", "topic": "Review collaboration handoff bundle"},
        {"runbook_id": "support-backup-restore", "topic": "Validate and inspect portable backup archive"},
        {"runbook_id": "support-product-shell", "topic": "Regenerate product shell artifacts"},
        {"runbook_id": "support-verification", "topic": "Run local verification commands"},
    ]


def _commands_table(commands: list[Any]) -> str:
    return _table("验证命令", commands, ("command", "purpose"))


def _limitations_table(limitations: list[Any]) -> str:
    return _table("已知限制", limitations, ("limitation_id", "severity", "description"))


def _runbooks_table(runbooks: list[Any]) -> str:
    return _table("支持 runbook", runbooks, ("runbook_id", "topic"))


def _table(title: str, rows: list[Any], columns: tuple[str, ...]) -> str:
    mapped = [_mapping(row) for row in rows]
    if not mapped:
        return f"<section><h2>{_html_text(title)}</h2><p>暂无内容。</p></section>"
    header = "".join(_th(column) for column in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_html_text(row.get(column))}</td>" for column in columns)
        + "</tr>"
        for row in mapped
    )
    return f"<section><h2>{_html_text(title)}</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _th(label: str) -> str:
    return f"<th>{_html_text(label)}</th>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; }
th { background: #eef2f7; font-size: 13px; }
td { font-size: 13px; }
""".strip()
