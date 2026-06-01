from __future__ import annotations

import json

import pytest
from scripts import build_product_shell, manage_product_workspace
from src.product_shell.workspace_store import (
    JsonWorkspaceRepository,
    build_default_workspace_state,
    render_workspace_state_html,
    save_workspace_view,
)


def test_json_workspace_repository_persists_saved_views_across_instances(tmp_path):
    store_path = tmp_path / "workspace_state.json"
    repository = JsonWorkspaceRepository(store_path)

    saved = repository.upsert_saved_view(
        {
            "view_id": "radar-trusted",
            "label": "可信叙事雷达",
            "surface": "narrative_radar",
            "selected_route": "/narratives/radar",
            "filters": {"trust_state": "trusted", "sector": "AI"},
            "sorting": {"field": "freshness", "direction": "desc"},
        },
        updated_at="2026-06-02T02:10:00+08:00",
    )
    reloaded = JsonWorkspaceRepository(store_path).load()

    assert store_path.exists()
    assert saved["version"] == "product-shell-workspace-state-v1"
    assert saved["storage_backend"] == "json_file"
    assert saved["summary"]["saved_view_count"] == 1
    assert saved["migration_contract"]["repository_interface"] == "WorkspaceRepository"
    assert saved["migration_contract"]["authoritative_records_mutated"] is False
    assert reloaded["saved_views"][0]["view_id"] == "radar-trusted"
    assert reloaded["saved_views"][0]["filters"] == {"sector": "AI", "trust_state": "trusted"}


def test_save_workspace_view_is_immutable_and_rejects_secrets():
    state = build_default_workspace_state(generated_at="2026-06-02T02:00:00+08:00")

    updated = save_workspace_view(
        state,
        {
            "view_id": "artifact-warnings",
            "label": "告警产物",
            "surface": "artifact_browser",
            "selected_route": "/artifacts",
            "filters": {"status": "warning"},
            "sorting": {"field": "generated_at", "direction": "desc"},
        },
        updated_at="2026-06-02T02:11:00+08:00",
    )

    assert state["saved_views"] == []
    assert updated["saved_views"][0]["view_id"] == "artifact-warnings"
    assert updated["summary"]["saved_view_count"] == 1

    with pytest.raises(ValueError, match="secret"):
        save_workspace_view(
            updated,
            {
                "view_id": "leaky",
                "label": "leaky",
                "surface": "artifact_browser",
                "filters": {"api_key": "should-not-persist"},
            },
        )

    with pytest.raises(ValueError, match="unsupported surface"):
        save_workspace_view(
            updated,
            {
                "view_id": "bad",
                "label": "bad",
                "surface": "provider_admin",
            },
        )


def test_workspace_state_html_is_chinese_and_discloses_contract(tmp_path):
    state = JsonWorkspaceRepository(tmp_path / "workspace_state.json").upsert_saved_view(
        {
            "view_id": "quality-review",
            "label": "质量复核",
            "surface": "narrative_quality",
            "selected_route": "/narratives/quality",
            "filters": {"severity": "medium"},
            "sorting": {"field": "severity", "direction": "desc"},
        },
        updated_at="2026-06-02T02:12:00+08:00",
    )

    html = render_workspace_state_html(state)

    assert "<h1>本地工作区状态</h1>" in html
    assert "质量复核" in html
    assert "不保存密钥" in html
    assert "不会修改可信市场数据或 Narrative Service 记录" in html


def test_build_product_shell_cli_writes_workspace_state_and_uses_existing_saved_views(tmp_path):
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    shell_dir = tmp_path / "shell"
    store_path = tmp_path / "workspace_state.json"
    JsonWorkspaceRepository(store_path).upsert_saved_view(
        {
            "view_id": "ops-readiness",
            "label": "生产就绪默认视图",
            "surface": "production_readiness",
            "selected_route": "/ops/production-readiness",
            "filters": {"mode": "demo"},
        },
        updated_at="2026-06-02T02:13:00+08:00",
    )

    exit_code = build_product_shell.main(
        [
            "--artifact-root",
            str(output_root),
            "--output-dir",
            str(shell_dir),
            "--workspace-store",
            str(store_path),
        ]
    )

    shell = json.loads((shell_dir / "product_shell.json").read_text())
    workspace = json.loads((shell_dir / "workspace_state.json").read_text())

    assert exit_code == 0
    assert shell["summary"]["workspace_saved_view_count"] == 1
    assert shell["workspace_state"]["saved_views"][0]["view_id"] == "ops-readiness"
    assert workspace["summary"]["saved_view_count"] == 1
    assert "<h1>本地工作区状态</h1>" in (shell_dir / "workspace_state.html").read_text()
    assert (shell_dir / "workspace_state.json").exists()


def test_workspace_route_is_registered_as_generated_product_shell_artifact():
    from src.product_shell.route_registry import build_product_shell_route_registry

    registry = build_product_shell_route_registry(
        artifact_index_path="outputs/product_shell/artifact_index.json",
    )
    route_ids = [route["route_id"] for route in registry["routes"]]
    workspace_route = next(route for route in registry["routes"] if route["route_id"] == "workspace_state")

    assert "workspace_state" in route_ids
    assert workspace_route["path"] == "/workspace/saved-views"
    assert workspace_route["data_source"]["json_path"] == "outputs/product_shell/round8-current/workspace_state.json"
    assert workspace_route["client_policy"]["provider_access_allowed"] is False


def test_manage_product_workspace_cli_saves_view_and_writes_html(tmp_path):
    store_path = tmp_path / "workspace_state.json"
    html_path = tmp_path / "workspace_state.html"

    exit_code = manage_product_workspace.main(
        [
            "save-view",
            "--store",
            str(store_path),
            "--html",
            str(html_path),
            "--view-id",
            "artifact-stale",
            "--label",
            "陈旧产物",
            "--surface",
            "artifact_browser",
            "--selected-route",
            "/artifacts",
            "--filters-json",
            '{"freshness_status":"stale"}',
            "--sorting-json",
            '{"field":"generated_at","direction":"desc"}',
            "--updated-at",
            "2026-06-02T02:20:00+08:00",
        ]
    )

    state = json.loads(store_path.read_text())

    assert exit_code == 0
    assert state["saved_views"][0]["view_id"] == "artifact-stale"
    assert state["saved_views"][0]["filters"] == {"freshness_status": "stale"}
    assert "<h1>本地工作区状态</h1>" in html_path.read_text()
