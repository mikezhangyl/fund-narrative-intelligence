from __future__ import annotations

import json
from pathlib import Path

from scripts import build_product_shell
from src.product_shell.artifact_index import (
    build_artifact_index,
    render_artifact_index_html,
)
from src.product_shell.route_registry import (
    build_product_shell_route_registry,
    render_route_registry_preview,
)
from src.product_shell.shell import (
    build_product_shell_payload,
    render_artifact_browser_html,
    render_product_home_html,
)


def test_route_registry_declares_product_pages_and_data_sources():
    registry = build_product_shell_route_registry(
        artifact_index_path="outputs/product_shell/artifact_index.json",
    )

    route_ids = [route["route_id"] for route in registry["routes"]]

    assert registry["version"] == "product-shell-route-registry-v1"
    assert route_ids == [
        "home",
        "narrative_radar",
        "narrative_quality",
        "portfolio_workspace",
        "production_readiness",
        "artifacts",
        "config_preflight",
    ]
    assert registry["summary"] == {
        "route_count": 7,
        "live_api_route_count": 2,
        "generated_artifact_route_count": 4,
        "fixture_demo_route_count": 1,
        "degraded_route_count": 0,
    }
    assert registry["routes"][2]["owner_service"] == "Narrative Service"
    assert registry["routes"][2]["data_source"]["type"] == "live_api"
    assert registry["routes"][3]["owner_service"] == "FNI"
    assert registry["routes"][3]["data_source"]["type"] == "generated_artifact"
    assert all(route["client_policy"]["score_recomputation_allowed"] is False for route in registry["routes"])
    assert all("provider_fetch" not in route["client_policy"]["forbidden_logic"] for route in registry["routes"])
    assert all("narrative_scoring" in route["client_policy"]["forbidden_logic"] for route in registry["routes"])


def test_route_registry_preview_is_human_readable_chinese_html():
    html = render_route_registry_preview(
        build_product_shell_route_registry(
            artifact_index_path="outputs/product_shell/artifact_index.json",
        )
    )

    assert "<h1>产品壳路由注册表</h1>" in html
    assert "叙事质量审计" in html
    assert "数据来源" in html
    assert "不在产品壳内重算评分" in html


def test_artifact_index_scans_existing_outputs_and_excludes_sensitive_paths(tmp_path):
    output_root = tmp_path / "outputs"
    _write_artifact_pair(
        output_root,
        "narrative_quality/round5_final",
        "narrative_quality_audit",
        status="completed",
        source_mode="narrative_service",
        freshness_status="fresh",
        warning_count=0,
        generated_at="2026-05-30T09:00:00+08:00",
    )
    _write_artifact_pair(
        output_root,
        "portfolio_narrative_workspace/round6-final",
        "portfolio_narrative_workspace",
        status="completed",
        source_mode="fixture_demo",
        freshness_status="fresh",
        warning_count=1,
        generated_at="2026-05-30T09:30:00+08:00",
    )
    _write_artifact_pair(
        output_root,
        "production_readiness_assistant/round7-final",
        "production_readiness_assistant",
        status="partial",
        source_mode="fixture_demo",
        freshness_status="breached",
        warning_count=2,
        generated_at="2026-05-30T10:00:00+08:00",
    )
    secret_path = output_root / "provider_secret_logs" / "api_token.json"
    secret_path.parent.mkdir(parents=True)
    secret_path.write_text('{"api_key": "leak"}', encoding="utf-8")

    index = build_artifact_index(output_root=output_root, project_root=tmp_path)

    assert index["version"] == "product-shell-artifact-index-v1"
    assert index["summary"] == {
        "artifact_count": 3,
        "html_link_count": 3,
        "json_link_count": 3,
        "warning_count": 3,
        "stale_or_superseded_count": 0,
    }
    assert [artifact["surface"] for artifact in index["artifacts"]] == [
        "Narrative quality audit",
        "Portfolio narrative workspace",
        "Production readiness assistant",
    ]
    assert all(not Path(artifact["json_path"]).is_absolute() for artifact in index["artifacts"])
    assert all(".." not in Path(artifact["json_path"]).parts for artifact in index["artifacts"])
    assert "api_key" not in json.dumps(index).lower()
    assert "token" not in json.dumps(index).lower()


def test_artifact_index_html_preview_lists_artifacts_in_chinese(tmp_path):
    output_root = tmp_path / "outputs"
    _write_artifact_pair(
        output_root,
        "narrative_quality/round5_final",
        "narrative_quality_audit",
        status="completed",
        source_mode="narrative_service",
        freshness_status="fresh",
        warning_count=0,
        generated_at="2026-05-30T09:00:00+08:00",
    )

    html = render_artifact_index_html(
        build_artifact_index(output_root=output_root, project_root=tmp_path)
    )

    assert "<h1>产物索引预览</h1>" in html
    assert "Narrative quality audit" in html
    assert "HTML 路径" in html
    assert "JSON 路径" in html


def test_product_shell_home_and_artifact_browser_use_registry_and_index(tmp_path):
    output_root = tmp_path / "outputs"
    _write_artifact_pair(
        output_root,
        "portfolio_narrative_workspace/round6-final",
        "portfolio_narrative_workspace",
        status="completed",
        source_mode="fixture_demo",
        freshness_status="fresh",
        warning_count=0,
        generated_at="2026-05-30T09:30:00+08:00",
    )
    registry = build_product_shell_route_registry(
        artifact_index_path="outputs/product_shell/artifact_index.json",
    )
    artifact_index = build_artifact_index(output_root=output_root, project_root=tmp_path)

    shell = build_product_shell_payload(route_registry=registry, artifact_index=artifact_index)
    home = render_product_home_html(shell)
    browser = render_artifact_browser_html(shell)

    assert shell["version"] == "product-shell-v1"
    assert shell["summary"]["route_count"] == 7
    assert shell["summary"]["artifact_count"] == 1
    assert "<h1>Fund Narrative Intelligence 产品首页</h1>" in home
    assert "Generated artifacts" in home
    assert "<h1>产物浏览器</h1>" in browser
    assert "portfolio_narrative_workspace.html" in browser
    assert "不在页面内重算雷达、质量或组合指标" in home


def test_build_product_shell_cli_writes_registry_index_home_and_browser(tmp_path):
    output_root = tmp_path / "outputs"
    _write_artifact_pair(
        output_root,
        "production_readiness_assistant/round7-final",
        "production_readiness_assistant",
        status="completed",
        source_mode="fixture_demo",
        freshness_status="fresh",
        warning_count=0,
        generated_at="2026-05-30T10:00:00+08:00",
    )
    shell_dir = tmp_path / "shell"

    exit_code = build_product_shell.main(
        [
            "--artifact-root",
            str(output_root),
            "--output-dir",
            str(shell_dir),
        ]
    )

    assert exit_code == 0
    assert json.loads((shell_dir / "route_registry.json").read_text())["summary"]["route_count"] == 7
    assert json.loads((shell_dir / "artifact_index.json").read_text())["summary"]["artifact_count"] == 1
    assert "<h1>Fund Narrative Intelligence 产品首页</h1>" in (shell_dir / "index.html").read_text()
    assert "<h1>产物浏览器</h1>" in (shell_dir / "artifact_browser.html").read_text()
    assert "<h1>产品壳路由注册表</h1>" in (shell_dir / "route_registry.html").read_text()
    assert "<h1>产物索引预览</h1>" in (shell_dir / "artifact_index.html").read_text()


def _write_artifact_pair(
    output_root: Path,
    relative_dir: str,
    stem: str,
    *,
    status: str,
    source_mode: str,
    freshness_status: str,
    warning_count: int,
    generated_at: str,
) -> None:
    directory = output_root / relative_dir
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": f"{stem}-v1",
        "generated_at": generated_at,
        "status": status,
        "summary": {"warning_count": warning_count},
        "source_mode": source_mode,
        "freshness_status": freshness_status,
    }
    (directory / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (directory / f"{stem}.html").write_text(
        f"<!doctype html><html><body><h1>{stem}</h1></body></html>",
        encoding="utf-8",
    )
