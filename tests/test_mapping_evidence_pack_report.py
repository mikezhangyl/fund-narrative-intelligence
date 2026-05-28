from __future__ import annotations

import json

from scripts import run_mapping_evidence_pack_report
from src.scanners.mapping_evidence_pack_report import (
    build_mapping_evidence_pack_report,
    render_html_report,
)


def test_mapping_evidence_pack_report_filters_symbols_and_keeps_candidate_status():
    report = build_mapping_evidence_pack_report(
        evidence_payload=_evidence_payload(),
        symbols=("600519", "000063"),
    )

    assert report["status"] == "candidate_untrusted"
    assert report["summary"] == {
        "requested_symbol_count": 2,
        "returned_pack_count": 2,
        "candidate_mapping_count": 2,
        "trusted_mapping_count": 0,
        "missing_symbol_count": 0,
    }
    assert report["packs"][0]["stock_code"] == "600519"
    assert report["packs"][0]["proposed_mappings"][0]["trust_status"] == "candidate_untrusted"
    assert report["packs"][0]["proposed_mappings"][0]["evidence_source_count"] == 2
    assert report["packs"][1]["proposed_mappings"][0]["exclusion_rationale"]
    assert report["promotion_decision"] == {
        "can_write_to_reviewed_mapping_store": False,
        "required_next_step": "human_review",
    }


def test_mapping_evidence_pack_html_contains_core_sections():
    report = build_mapping_evidence_pack_report(
        evidence_payload=_evidence_payload(),
        symbols=("600519",),
    )

    html = render_html_report(report)

    assert "<h1>股票叙事映射证据包</h1>" in html
    assert "贵州茅台" in html
    assert "证据" in html
    assert "映射理由" in html
    assert "排除理由" in html
    assert "candidate_untrusted" in html


def test_run_mapping_evidence_pack_report_writes_json_and_html(tmp_path):
    evidence_path = tmp_path / "mapping_evidence_packs.json"
    evidence_path.write_text(json.dumps(_evidence_payload()), encoding="utf-8")

    exit_code = run_mapping_evidence_pack_report.main(
        [
            "--evidence-path",
            str(evidence_path),
            "--symbols",
            "600519,000063",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "mapping_evidence_pack_report.json").read_text())
    html = (tmp_path / "mapping_evidence_pack_report.html").read_text()

    assert exit_code == 0
    assert payload["summary"]["returned_pack_count"] == 2
    assert payload["packs"][0]["stock_code"] == "600519"
    assert "<h1>股票叙事映射证据包</h1>" in html


def _evidence_payload() -> dict:
    return {
        "version": "mapping-evidence-pack-v0",
        "trust_status": "candidate_untrusted",
        "packs": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "proposed_mappings": [
                    {
                        "narrative_id": "N_BAIJIU_CONSUMPTION",
                        "narrative_name": "高端白酒消费",
                        "trust_status": "candidate_untrusted",
                        "mapping_rationale": "主营产品和品牌事实直接支撑白酒消费叙事。",
                        "exclusion_rationale": ["不是一般食品饮料泛标签。"],
                        "confidence_components": {
                            "business_relevance": 0.95,
                            "evidence_quality": 0.8,
                        },
                        "evidence_items": [
                            {"source_name": "Annual report", "source_url": "https://example.test/a"},
                            {"source_name": "Company ESG", "source_url": "https://example.test/b"},
                        ],
                    }
                ],
            },
            {
                "stock_code": "000063",
                "stock_name": "中兴通讯",
                "proposed_mappings": [
                    {
                        "narrative_id": "N_COMMUNICATION_EQUIPMENT",
                        "narrative_name": "通信设备与连接器件",
                        "trust_status": "candidate_untrusted",
                        "mapping_rationale": "业务事实支撑通信设备叙事。",
                        "exclusion_rationale": ["不自动等同于光模块。"],
                        "confidence_components": {
                            "business_relevance": 0.85,
                            "evidence_quality": 0.75,
                        },
                        "evidence_items": [
                            {"source_name": "Annual report", "source_url": "https://example.test/c"}
                        ],
                    }
                ],
            },
        ],
    }
