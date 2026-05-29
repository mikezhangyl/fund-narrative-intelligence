from __future__ import annotations

import json

from scripts import run_reviewable_fund_report_pack
from src.orchestrator import run_pipeline
from src.scanners.reviewable_fund_report_pack import (
    build_reviewable_fund_report_pack,
    render_html_report,
)


def test_reviewable_fund_report_pack_links_core_artifacts_and_review_entries(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)

    pack = build_reviewable_fund_report_pack(
        artifact_root=tmp_path,
        reference_artifacts={
            "fund_holding_exposure": "fund_holding_exposure_report.html",
            "narrative_matrix": "fund_narrative_exposure_matrix_report.html",
            "mapping_evidence_pack": "mapping_evidence_pack_report.html",
            "change_monitor": "fund_narrative_change_monitor_report.html",
        },
    )

    assert pack["version"] == "reviewable-fund-report-pack-v1"
    assert pack["status"] == "review_ready"
    assert pack["fund"]["fund_code"] == "000001"
    assert pack["manifest"]["run_id"].startswith("fund_000001_")
    assert pack["summary"]["holding_count"] > 0
    assert pack["summary"]["artifact_count"] >= 7
    assert pack["source_modes"]["provider_mode"] == "mock"
    assert pack["trust_disclosure"]["candidate_outputs"] == "candidate_untrusted"
    assert pack["trust_disclosure"]["trusted_promotion"] == "disabled"
    assert "fund_000001_raw.json" in {
        artifact["path"] for artifact in pack["artifact_links"]
    }
    assert "fund_narrative_exposure_matrix_report.html" in {
        artifact["path"] for artifact in pack["reference_artifacts"]
    }
    assert pack["data_gap_summary"]["mock_layer_count"] > 0
    assert pack["review_workspace"]["review_item_count"] == 0


def test_reviewable_fund_report_pack_html_is_chinese_static_reader_surface(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    pack = build_reviewable_fund_report_pack(artifact_root=tmp_path)

    html = render_html_report(pack)

    assert "<h1>基金审查报告包</h1>" in html
    assert "持仓概览" in html
    assert "叙事暴露" in html
    assert "来源与数据缺口" in html
    assert "Review Queue" in html
    assert "candidate_untrusted" in html
    assert "不构成投资建议" in html
    assert "fund_000001_report.html" in html


def test_run_reviewable_fund_report_pack_writes_json_and_html(tmp_path):
    artifact_root = tmp_path / "pipeline"
    artifact_root.mkdir()
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=artifact_root)

    exit_code = run_reviewable_fund_report_pack.main(
        [
            "--artifact-root",
            str(artifact_root),
            "--output-dir",
            str(tmp_path),
            "--reference-artifact",
            "narrative_matrix=fund_narrative_exposure_matrix_report.html",
        ]
    )

    payload = json.loads((tmp_path / "reviewable_fund_report_pack.json").read_text())
    html = (tmp_path / "reviewable_fund_report_pack.html").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["status"] == "review_ready"
    assert payload["reference_artifacts"][0]["artifact_key"] == "narrative_matrix"
    assert "基金审查报告包" in html
