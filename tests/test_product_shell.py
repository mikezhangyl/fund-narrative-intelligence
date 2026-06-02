from __future__ import annotations

import json
from pathlib import Path

from scripts import build_product_shell
from src.product_shell.artifact_index import (
    build_artifact_index,
    render_artifact_index_html,
)
from src.product_shell.narrative_data import (
    build_narrative_data_snapshot,
    render_narrative_data_html,
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
        "narrative_data",
        "narrative_quality",
        "fresh_narrative_digest",
        "narrative_timeline_search",
        "narrative_evidence_graph",
        "narrative_research_export_pack",
        "historical_replay",
        "replay_stability_evaluation",
        "replay_alert_review",
        "collaboration_handoff",
        "backup_restore_archive",
        "portfolio_workspace",
        "workspace_state",
        "production_readiness",
        "source_quality",
        "artifacts",
        "config_preflight",
    ]
    assert registry["summary"] == {
        "route_count": 19,
        "live_api_route_count": 2,
        "generated_artifact_route_count": 17,
        "fixture_demo_route_count": 0,
        "degraded_route_count": 0,
    }
    assert registry["routes"][2]["owner_service"] == "FNI"
    assert registry["routes"][2]["data_source"]["type"] == "generated_artifact"
    assert registry["routes"][2]["data_source"]["json_path"] == "outputs/product_shell/round8-current/narrative_data.json"
    assert registry["routes"][3]["owner_service"] == "Narrative Service"
    assert registry["routes"][3]["data_source"]["type"] == "live_api"
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


def test_narrative_data_snapshot_reads_existing_service_artifacts(tmp_path):
    _write_real_narrative_sources(tmp_path)

    snapshot = build_narrative_data_snapshot(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
        generated_at="2026-06-01T08:00:00+00:00",
    )

    assert snapshot["version"] == "product-shell-narrative-data-v1"
    assert snapshot["generated_at"] == "2026-06-01T08:00:00+00:00"
    assert snapshot["summary"] == {
        "narrative_count": 2,
        "candidate_narrative_count": 1,
        "stock_mapping_count": 2,
        "evidence_pack_count": 1,
        "quality_scorecard_count": 1,
        "quality_issue_count": 1,
        "extraction_issue_count": 1,
        "available_source_count": 6,
        "missing_source_count": 0,
    }
    assert snapshot["consumer_policy"]["quality_authority"] == "narrative_service"
    assert snapshot["consumer_policy"]["fni_recomputes_quality"] is False
    assert snapshot["narratives"][0]["narrative_id"] == "N_AI"
    assert snapshot["candidate_narratives"][0]["candidate_narrative_id"] == "C_OPTICAL"
    assert snapshot["evidence_pack_scorecards"][0]["evidence_pack_id"] == "EPACK_TEST"
    assert snapshot["service_health"]["conformance"]["status"] == "pass"
    assert snapshot["service_health"]["provider_smoke"]["status"] == "pass"
    assert "super-secret-token" not in json.dumps(snapshot, ensure_ascii=False)


def test_narrative_data_snapshot_marks_missing_sources(tmp_path):
    _write_real_narrative_sources(tmp_path, include_quality_audit=False)

    snapshot = build_narrative_data_snapshot(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
    )

    assert snapshot["summary"]["available_source_count"] == 5
    assert snapshot["summary"]["missing_source_count"] == 1
    assert any(
        source["status"] == "missing"
        and source["path"] == "outputs/narrative_quality/round5_final/narrative_quality_audit.json"
        for source in snapshot["source_artifacts"]
    )


def test_narrative_data_html_is_chinese_and_uses_real_snapshot(tmp_path):
    _write_real_narrative_sources(tmp_path)

    html = render_narrative_data_html(
        build_narrative_data_snapshot(
            project_root=tmp_path,
            output_root=tmp_path / "outputs",
        )
    )

    assert "<h1>真实叙事数据</h1>" in html
    assert "来自现有 Narrative Service / FNI artifacts" in html
    assert "人工智能" in html
    assert "EPACK_TEST" in html
    assert "不在页面内重算评分" in html


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

    narrative_data = {
        "summary": {
            "narrative_count": 2,
            "candidate_narrative_count": 1,
            "stock_mapping_count": 2,
            "evidence_pack_count": 1,
            "quality_issue_count": 1,
            "extraction_issue_count": 1,
        },
        "source_artifacts": [],
    }

    shell = build_product_shell_payload(
        route_registry=registry,
        artifact_index=artifact_index,
        narrative_data=narrative_data,
    )
    home = render_product_home_html(shell)
    browser = render_artifact_browser_html(shell)

    assert shell["version"] == "product-shell-v1"
    assert shell["summary"]["route_count"] == 19
    assert shell["summary"]["artifact_count"] == 1
    assert shell["summary"]["narrative_count"] == 2
    assert "<h1>Fund Narrative Intelligence 产品首页</h1>" in home
    assert "真实叙事数据" in home
    assert "正式叙事: 2" in home
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
    assert json.loads((shell_dir / "route_registry.json").read_text())["summary"]["route_count"] == 19
    assert json.loads((shell_dir / "artifact_index.json").read_text())["summary"]["artifact_count"] == 1
    assert (shell_dir / "narrative_data.json").exists()
    assert (shell_dir / "narrative_data.html").exists()
    assert (shell_dir / "workspace_state.json").exists()
    assert (shell_dir / "workspace_state.html").exists()
    assert "<h1>Fund Narrative Intelligence 产品首页</h1>" in (shell_dir / "index.html").read_text()
    assert "<h1>产物浏览器</h1>" in (shell_dir / "artifact_browser.html").read_text()
    assert "<h1>产品壳路由注册表</h1>" in (shell_dir / "route_registry.html").read_text()
    assert "<h1>产物索引预览</h1>" in (shell_dir / "artifact_index.html").read_text()
    assert "<h1>真实叙事数据</h1>" in (shell_dir / "narrative_data.html").read_text()
    assert "<h1>来源质量仪表盘</h1>" in (shell_dir / "source_quality_dashboard.html").read_text()


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


def _write_real_narrative_sources(tmp_path: Path, *, include_quality_audit: bool = True) -> None:
    registry_dir = tmp_path / "data" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "narrative_registry.reviewed.json").write_text(
        json.dumps(
            {
                "version": "reviewed-registry-v1",
                "trust_metadata": {"trust_status": "reviewed"},
                "narratives": [
                    {
                        "narrative_id": "N_AI",
                        "display_name": "人工智能",
                        "canonical_name_zh": "人工智能",
                        "status": "active",
                        "human_review_status": "approved",
                        "secret_note": "super-secret-token",
                    },
                    {
                        "narrative_id": "N_OPTICAL",
                        "display_name": "光模块",
                        "status": "active",
                        "human_review_status": "approved",
                    },
                ],
                "candidate_narratives": [
                    {
                        "candidate_narrative_id": "C_OPTICAL",
                        "display_name": "光通信",
                        "confidence": 0.82,
                        "status": "promoted",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (registry_dir / "stock_narrative_mappings.reviewed.json").write_text(
        json.dumps(
            {
                "version": "reviewed-mappings-v1",
                "mappings": [
                    {"stock_code": "000063", "narrative_id": "N_OPTICAL", "confidence": 0.8},
                    {"stock_code": "600519", "narrative_id": "N_BAIJIU", "confidence": 0.9},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (registry_dir / "mapping_evidence_packs.v0.json").write_text(
        json.dumps(
            {
                "version": "mapping-evidence-packs-v0",
                "trust_status": "candidate_untrusted",
                "packs": [
                    {
                        "stock_code": "000063",
                        "stock_name": "中兴通讯",
                        "proposed_mappings": [{"narrative_id": "N_OPTICAL"}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if include_quality_audit:
        quality_dir = tmp_path / "outputs" / "narrative_quality" / "round5_final"
        quality_dir.mkdir(parents=True, exist_ok=True)
        (quality_dir / "narrative_quality_audit.json").write_text(
            json.dumps(
                {
                    "version": "quality-audit-v1",
                    "generated_at": "2026-05-29T17:29:35+00:00",
                    "formula_version": "evidence-quality-deterministic-v1",
                    "consumer_policy": {
                        "quality_authority": "narrative_service",
                        "fni_recomputes_quality": False,
                    },
                    "summary": {"issue_count": 1, "needs_review_extraction_count": 1},
                    "issues": [{"issue_id": "Q1", "severity": "medium", "message": "需复核"}],
                    "extraction_confidence_issues": [
                        {"source_event_id": "EVT1", "status": "needs_review"}
                    ],
                    "evidence_pack_scorecards": [
                        {
                            "evidence_pack_id": "EPACK_TEST",
                            "stock_code": "000063",
                            "narrative_id": "N_OPTICAL",
                            "quality_score": 78,
                            "grade": "B",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    conformance_dir = (
        tmp_path
        / "outputs"
        / "stock_narrative_service_acceptance"
        / "round5-final"
        / "conformance"
    )
    conformance_dir.mkdir(parents=True, exist_ok=True)
    (conformance_dir / "narrative_service_conformance_report.json").write_text(
        json.dumps(
            {
                "version": "conformance-v1",
                "generated_at": "2026-05-29T17:29:35+00:00",
                "result": {"status": "pass", "contract_version": "v1", "api_key": "super-secret-token"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    smoke_dir = (
        tmp_path
        / "outputs"
        / "stock_narrative_service_acceptance"
        / "round5-final"
        / "provider_smoke"
    )
    smoke_dir.mkdir(parents=True, exist_ok=True)
    (smoke_dir / "narrative_service_provider_smoke.json").write_text(
        json.dumps(
            {
                "version": "provider-smoke-v1",
                "generated_at": "2026-05-29T17:29:35+00:00",
                "result": {"status": "pass", "provider": "local", "warning_count": 0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
