from __future__ import annotations

import json
from pathlib import Path

from scripts import build_product_shell
from src.product_shell.route_registry import build_product_shell_route_registry
from src.product_shell.source_quality import (
    build_source_quality_dashboard,
    render_source_quality_dashboard_html,
)


def test_source_quality_dashboard_combines_existing_source_artifacts(tmp_path):
    _write_source_quality_artifacts(tmp_path)

    dashboard = build_source_quality_dashboard(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
        generated_at="2026-06-02T10:00:00+00:00",
    )
    serialized = json.dumps(dashboard, ensure_ascii=False)

    assert dashboard["version"] == "product-shell-source-quality-dashboard-v1"
    assert dashboard["generated_at"] == "2026-06-02T10:00:00+00:00"
    assert dashboard["status"] == "degraded"
    assert dashboard["summary"] == {
        "source_count": 3,
        "trusted_fact_count": 1,
        "degraded_source_count": 2,
        "missing_artifact_count": 0,
        "stale_artifact_count": 0,
    }
    assert dashboard["consumer_policy"] == {
        "provider_access_allowed": False,
        "reliability_recomputation_allowed": False,
        "owner_boundary": "Gateway owns acquisition; FNI displays generated contracts, probes, and reports.",
    }
    official = next(row for row in dashboard["sources"] if row["source_id"] == "sec_edgar_filings")
    assert official["source_type"] == "official_disclosure"
    assert official["owner_service"] == "stock-data-gateway"
    assert official["trust_tier"] == "trusted_fact"
    assert official["source_quality_label"] == "Trusted Fact"
    assert official["license_scope"] == "metadata_and_public_document_reference"
    assert official["retention_policy"] == "metadata_and_permitted_excerpt"
    assert official["anti_bot_risk"] == "low"
    assert official["status"] == "ok"
    assert official["artifact_paths"]["governance_json"].endswith("source_governance_report.json")
    assert "must-not-leak" not in serialized


def test_source_quality_dashboard_degrades_when_artifacts_are_missing(tmp_path):
    dashboard = build_source_quality_dashboard(
        project_root=tmp_path,
        output_root=tmp_path / "outputs",
    )

    assert dashboard["status"] == "degraded"
    assert dashboard["summary"]["missing_artifact_count"] == 4
    assert dashboard["sources"] == []
    assert all(artifact["status"] == "missing" for artifact in dashboard["artifacts"])


def test_source_quality_dashboard_html_is_chinese_and_cites_review_source(tmp_path):
    _write_source_quality_artifacts(tmp_path)

    html = render_source_quality_dashboard_html(
        build_source_quality_dashboard(
            project_root=tmp_path,
            output_root=tmp_path / "outputs",
        )
    )

    assert "<h1>来源质量仪表盘</h1>" in html
    assert "SEC EDGAR filings" in html
    assert "Gateway owns acquisition" in html
    assert "pm-architect-stage-review-round4-round13-2026-06-02.html" in html
    assert "不重新计算来源可靠性分" in html


def test_route_registry_includes_source_quality_dashboard_route():
    registry = build_product_shell_route_registry(
        artifact_index_path="outputs/product_shell/artifact_index.json",
    )

    route = next(route for route in registry["routes"] if route["route_id"] == "source_quality")

    assert route["path"] == "/sources/quality"
    assert route["owner_service"] == "FNI"
    assert route["data_source"]["type"] == "generated_artifact"
    assert route["data_source"]["json_path"] == (
        "outputs/product_shell/round8-current/source_quality_dashboard.json"
    )
    assert registry["summary"]["route_count"] == 11


def test_build_product_shell_cli_writes_source_quality_dashboard(tmp_path):
    output_root = tmp_path / "outputs"
    _write_source_quality_artifacts(tmp_path)
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
    assert (shell_dir / "source_quality_dashboard.json").exists()
    assert (shell_dir / "source_quality_dashboard.html").exists()
    assert "<h1>来源质量仪表盘</h1>" in (
        shell_dir / "source_quality_dashboard.html"
    ).read_text()


def _write_source_quality_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    governance_dir = output_root / "source_governance" / "latest"
    reliability_dir = output_root / "source_reliability" / "latest"
    schema_dir = output_root / "source_schema_v2" / "latest"
    probe_dir = output_root / "narrative_source_gateway_probe" / "current"
    for directory in (governance_dir, reliability_dir, schema_dir, probe_dir):
        directory.mkdir(parents=True)

    (governance_dir / "source_governance_report.json").write_text(
        json.dumps(
            {
                "version": "source-governance-evaluation-v1",
                "generated_at": "2026-06-02T09:00:00+00:00",
                "decisions": [
                    {
                        "source_id": "sec_edgar_filings",
                        "display_name": "SEC EDGAR filings",
                        "acquisition_mode": "official_api",
                        "owner_service": "stock-data-gateway",
                        "license_scope": "metadata_and_public_document_reference",
                        "retention_policy": "metadata_and_permitted_excerpt",
                        "anti_bot_risk": "low",
                        "gate_status": "passed",
                        "blocked_reasons": [],
                    },
                    {
                        "source_id": "stocktwits_heat",
                        "display_name": "Stocktwits heat",
                        "acquisition_mode": "official_api",
                        "owner_service": "stock-data-gateway",
                        "license_scope": "metadata_and_permitted_excerpt",
                        "retention_policy": "no_profile_retention",
                        "anti_bot_risk": "medium",
                        "gate_status": "passed",
                        "blocked_reasons": [],
                    },
                    {
                        "source_id": "forbidden_social_scrape",
                        "display_name": "Forbidden social scrape",
                        "acquisition_mode": "community_page_crawler",
                        "owner_service": "stock-data-gateway",
                        "license_scope": "none",
                        "retention_policy": "do_not_store",
                        "anti_bot_risk": "high",
                        "gate_status": "blocked",
                        "blocked_reasons": ["prohibited_behavior_declared"],
                        "secret_note": "must-not-leak",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (governance_dir / "source_governance_report.html").write_text(
        "<!doctype html><html><body>governance</body></html>",
        encoding="utf-8",
    )
    (reliability_dir / "source_reliability_report.json").write_text(
        json.dumps(
            {
                "version": "source-reliability-report-v1",
                "generated_at": "2026-06-02T09:05:00+00:00",
                "scores": [
                    {
                        "source_id": "sec_edgar_filings",
                        "source_class": "official_disclosure",
                        "label": "Trusted Fact",
                        "score": 0.89,
                        "trusted_fact_allowed": True,
                        "warnings": [],
                    },
                    {
                        "source_id": "stocktwits_heat",
                        "source_class": "social_community",
                        "label": "Heat Signal",
                        "score": 0.65,
                        "trusted_fact_allowed": False,
                        "warnings": ["social_sources_require_corroboration_for_trusted_fact"],
                    },
                    {
                        "source_id": "forbidden_social_scrape",
                        "source_class": "social_community",
                        "label": "Avoid",
                        "score": 0.1,
                        "trusted_fact_allowed": False,
                        "warnings": ["blocked_by_governance"],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (reliability_dir / "source_reliability_report.html").write_text(
        "<!doctype html><html><body>reliability</body></html>",
        encoding="utf-8",
    )
    (schema_dir / "source_schema_v2_report.json").write_text(
        json.dumps(
            {
                "version": "source-schema-v2-report-v1",
                "generated_at": "2026-06-02T09:10:00+00:00",
                "supported_source_classes": [
                    "official_disclosure",
                    "licensed_news",
                    "public_web",
                    "social_community",
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (schema_dir / "source_schema_v2_report.html").write_text(
        "<!doctype html><html><body>schema</body></html>",
        encoding="utf-8",
    )
    (probe_dir / "narrative_source_gateway_probe.json").write_text(
        json.dumps(
            {
                "version": "narrative-source-gateway-probe-v1",
                "generated_at": "2026-06-02T09:15:00+00:00",
                "source_results": [
                    {
                        "source_kind": "official_filings",
                        "row_count": 3,
                        "degradation_events": [],
                        "meta": {
                            "trust_tier": "trusted_fact",
                            "source_quality": {"label": "official_metadata"},
                        },
                    },
                    {
                        "source_kind": "social_heat",
                        "row_count": 0,
                        "degradation_events": ["SOCIAL_SOURCE_DISABLED"],
                        "meta": {
                            "trust_tier": "heat_signal_only",
                            "source_quality": {"label": "disabled"},
                        },
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
