from __future__ import annotations

import json
from pathlib import Path

from scripts import run_product_shell_release_check
from src.product_shell.release import (
    build_release_preflight,
    render_config_preflight_html,
)
from src.product_shell.route_registry import build_product_shell_route_registry


def test_release_preflight_demo_mode_redacts_secrets_without_live_urls(tmp_path):
    payload = build_release_preflight(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
        mode="demo",
        env={
            "TUSHARE_TOKEN": "super-secret-token",
            "MARKET_DATA_GATEWAY_URL": "",
            "NARRATIVE_SERVICE_URL": "",
        },
        generated_at="2026-06-02T09:00:00+00:00",
    )

    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["version"] == "product-shell-release-preflight-v1"
    assert payload["mode"] == "demo"
    assert payload["status"] == "ok"
    assert payload["generated_at"] == "2026-06-02T09:00:00+00:00"
    assert payload["summary"]["degraded_count"] == 0
    assert payload["summary"]["secret_redaction_count"] == 1
    assert payload["validation_command"] == (
        "uv run python scripts/run_product_shell_release_check.py --mode demo"
    )
    assert "super-secret-token" not in serialized
    assert "***REDACTED***" in serialized
    assert any(
        check["check_id"] == "narrative_service_url"
        and check["status"] == "optional_missing"
        for check in payload["checks"]
    )


def test_release_preflight_live_mode_degrades_missing_required_services(tmp_path):
    payload = build_release_preflight(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
        mode="live",
        env={},
    )

    assert payload["status"] == "degraded"
    assert payload["summary"]["degraded_count"] == 2
    assert payload["summary"]["provider_smoke_executed"] is False
    assert {check["check_id"] for check in payload["checks"] if check["status"] == "missing"} == {
        "market_data_gateway_url",
        "narrative_service_url",
    }
    assert all("smoke" not in check["check_id"] for check in payload["checks"])
    assert payload["startup_order"] == [
        {
            "step": 1,
            "service": "stock-data-gateway",
            "required_in_demo": False,
            "required_in_live": True,
        },
        {
            "step": 2,
            "service": "stock-narrative-service",
            "required_in_demo": False,
            "required_in_live": True,
        },
        {
            "step": 3,
            "service": "fund-narrative-intelligence product shell",
            "required_in_demo": True,
            "required_in_live": True,
        },
    ]


def test_config_preflight_html_is_chinese_and_points_to_safe_commands(tmp_path):
    payload = build_release_preflight(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
        mode="live",
        env={"NARRATIVE_SERVICE_API_KEY": "must-not-render"},
    )

    html = render_config_preflight_html(payload)

    assert "<h1>配置与预检</h1>" in html
    assert "预检不是 provider smoke" in html
    assert "uv run python scripts/run_product_shell_release_check.py --mode demo" in html
    assert "docs/product/stock-narrative-service-runbook.md" in html
    assert "must-not-render" not in html
    assert "***REDACTED***" in html


def test_route_registry_config_preflight_points_to_generated_preflight_artifact():
    registry = build_product_shell_route_registry(
        artifact_index_path="outputs/product_shell/artifact_index.json",
    )

    route = next(route for route in registry["routes"] if route["route_id"] == "config_preflight")

    assert route["data_source"]["type"] == "generated_artifact"
    assert route["data_source"]["json_path"] == (
        "outputs/product_shell/round8-current/config_preflight.json"
    )
    assert route["data_source"]["html_path"] == (
        "outputs/product_shell/round8-current/config_preflight.html"
    )
    assert route["data_source"]["source"] == "product shell release preflight"
    assert registry["summary"]["generated_artifact_route_count"] == 15
    assert registry["summary"]["fixture_demo_route_count"] == 0


def test_release_check_cli_generates_manifest_and_acceptance_artifacts(tmp_path):
    output_root = tmp_path / "outputs"
    _write_artifact_pair(
        output_root,
        "production_readiness_assistant/round7-final",
        "production_readiness_assistant",
    )
    shell_dir = tmp_path / "release"

    exit_code = run_product_shell_release_check.main(
        [
            "--artifact-root",
            str(output_root),
            "--output-dir",
            str(shell_dir),
            "--mode",
            "demo",
        ],
        env={"TUSHARE_TOKEN": "must-not-leak"},
    )

    manifest = json.loads((shell_dir / "release_manifest.json").read_text())
    checklist = json.loads((shell_dir / "acceptance_checklist.json").read_text())
    serialized = json.dumps(manifest, ensure_ascii=False) + json.dumps(checklist, ensure_ascii=False)

    assert exit_code == 0
    assert manifest["version"] == "product-shell-release-manifest-v1"
    assert manifest["status"] == "ok"
    assert manifest["mode"] == "demo"
    assert manifest["summary"]["missing_expected_artifact_count"] == 0
    assert manifest["commands"]["release_check"] == (
        "uv run python scripts/run_product_shell_release_check.py --mode demo"
    )
    assert {artifact["artifact_id"] for artifact in manifest["expected_artifacts"]} >= {
        "product_home_html",
        "artifact_browser_html",
        "route_registry_json",
        "config_preflight_html",
        "release_manifest_json",
        "acceptance_checklist_html",
    }
    assert checklist["version"] == "product-shell-acceptance-checklist-v1"
    assert checklist["status"] == "pass"
    assert {item["check_id"] for item in checklist["checks"]} >= {
        "product_shell_opens",
        "major_routes_render",
        "artifact_browser_links",
        "config_preflight_redacts_secrets",
        "release_manifest_generated",
    }
    assert "<h1>本地发布包 Manifest</h1>" in (shell_dir / "release_manifest.html").read_text()
    assert "<h1>产品壳验收清单</h1>" in (shell_dir / "acceptance_checklist.html").read_text()
    assert "must-not-leak" not in serialized
    assert "must-not-leak" not in (shell_dir / "config_preflight.html").read_text()


def test_release_check_live_mode_writes_degraded_artifacts_for_missing_services(tmp_path):
    shell_dir = tmp_path / "release"

    exit_code = run_product_shell_release_check.main(
        [
            "--artifact-root",
            str(tmp_path / "outputs"),
            "--output-dir",
            str(shell_dir),
            "--mode",
            "live",
        ],
        env={},
    )

    manifest = json.loads((shell_dir / "release_manifest.json").read_text())
    checklist = json.loads((shell_dir / "acceptance_checklist.json").read_text())

    assert exit_code == 1
    assert manifest["status"] == "degraded"
    assert checklist["status"] == "fail"
    assert any(
        item["responsible_surface"] == "stock-data-gateway"
        and item["status"] == "fail"
        for item in checklist["checks"]
    )
    assert any(
        item["responsible_surface"] == "stock-narrative-service"
        and item["status"] == "fail"
        for item in checklist["checks"]
    )


def _write_artifact_pair(output_root: Path, relative_dir: str, stem: str) -> None:
    directory = output_root / relative_dir
    directory.mkdir(parents=True)
    payload = {
        "version": f"{stem}-v1",
        "generated_at": "2026-06-02T09:00:00+00:00",
        "status": "completed",
        "summary": {"warning_count": 0},
        "source_mode": "fixture_demo",
        "freshness_status": "fresh",
    }
    (directory / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (directory / f"{stem}.html").write_text(
        f"<!doctype html><html><body><h1>{stem}</h1></body></html>",
        encoding="utf-8",
    )
