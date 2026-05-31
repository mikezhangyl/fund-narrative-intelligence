from __future__ import annotations

import json

from scripts import run_cninfo_disclosure_event_smoke
from src.scanners.cninfo_disclosure_events import (
    build_cninfo_disclosure_event_report,
    classify_cninfo_disclosure_event,
    render_cninfo_disclosure_event_html,
)


def test_classifies_cninfo_metadata_event_categories():
    examples = [
        ("签署重大合同暨中标公告", "重大合同", "major_contract_order"),
        ("关于对外投资建设新能源项目的公告", "对外投资", "investment_project"),
        ("关于生产基地扩产及产能建设的公告", "项目建设", "capacity_expansion"),
        ("发行股份购买资产暨重大资产重组预案", "资产重组", "ma_restructuring"),
        ("关于收到监管问询函及行政处罚的公告", "监管函", "regulatory_inquiry_penalty"),
        ("2026年度业绩预告暨一季度报告", "业绩预告", "performance_forecast_report"),
        ("2025年年度股东大会法律意见书", "股东大会", "shareholder_meeting_governance"),
        ("向特定对象发行股票募集资金的公告", "再融资", "financing_refinancing"),
        ("重大诉讼及仲裁进展公告", "诉讼仲裁", "litigation_arbitration"),
        ("关于公司股票可能被实施退市风险警示的公告", "风险提示", "risk_warning"),
    ]

    assert [
        classify_cninfo_disclosure_event({"title": title, "category": category})["event_class"]
        for title, category, _expected in examples
    ] == [expected for _title, _category, expected in examples]


def test_unknown_cninfo_category_is_metadata_only_with_reason():
    classification = classify_cninfo_disclosure_event(
        {"title": "关于召开说明会的公告", "category": "其他公告"}
    )

    assert classification == {
        "event_class": "unknown_metadata",
        "event_label_zh": "未支持分类公告",
        "sentiment": "neutral",
        "unsupported_category_reason": "no_supported_keyword_match",
    }


def test_builds_cninfo_disclosure_source_events_with_trust_and_quality():
    report = build_cninfo_disclosure_event_report(
        announcements_payload=_cninfo_fixture(),
        fetched_at="2026-06-01T00:00:00+00:00",
    )

    assert report["version"] == "cninfo-disclosure-events-v1"
    assert report["data_quality"] == "fresh"
    assert report["summary"] == {
        "announcement_count": 3,
        "event_count": 3,
        "unknown_category_count": 1,
        "missing_stock_code_count": 0,
        "source_quality": "fresh",
    }
    first = report["events"][0]
    assert first["source_type"] == "announcement"
    assert first["source_trust_tier"] == "trusted_fact"
    assert first["evidence_granularity"] == "metadata_only"
    assert first["stock_codes"] == ["000001"]
    assert first["source_metadata"]["provider"] == "cninfo-announcement"
    assert first["source_metadata"]["event_class"] == "shareholder_meeting_governance"
    assert first["source_metadata"]["fetched_at"] == "2026-06-01T00:00:00+00:00"
    assert first["source_metadata"]["source_trust_tier"] == "trusted_fact"
    assert first["source_metadata"]["evidence_granularity"] == "metadata_only"
    assert "unsupported_category_reason" in report["events"][2]["source_metadata"]


def test_cninfo_disclosure_html_is_chinese_and_discloses_metadata_only():
    html = render_cninfo_disclosure_event_html(
        build_cninfo_disclosure_event_report(
            announcements_payload=_cninfo_fixture(),
            fetched_at="2026-06-01T00:00:00+00:00",
        )
    )

    assert "<h1>CNINFO 官方公告事件分类</h1>" in html
    assert "trusted_fact" in html
    assert "metadata_only" in html
    assert "不解析 PDF 正文" in html
    assert "shareholder_meeting_governance" in html


def test_cninfo_disclosure_smoke_cli_writes_json_and_html(tmp_path):
    input_path = tmp_path / "cninfo.json"
    input_path.write_text(json.dumps(_cninfo_fixture(), ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "out"

    exit_code = run_cninfo_disclosure_event_smoke.main(
        [
            "--stock-code",
            "000001",
            "--as-of-date",
            "2026-06-01",
            "--input-json",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads((output_dir / "cninfo_disclosure_events.json").read_text())
    html = (output_dir / "cninfo_disclosure_events.html").read_text()

    assert payload["summary"]["event_count"] == 3
    assert payload["events"][0]["source_trust_tier"] == "trusted_fact"
    assert "<h1>CNINFO 官方公告事件分类</h1>" in html


def _cninfo_fixture() -> dict[str, object]:
    return {
        "version": "cninfo-announcement-v1",
        "data_quality": "fresh",
        "announcements": [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "2025年年度股东大会法律意见书",
                "category": "股东大会",
                "announcement_date": "2026-05-22",
                "source": "cninfo",
                "source_url": "https://static.cninfo.com.cn/finalpage/2026-05-22/test.PDF",
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "2026年度业绩预告",
                "category": "业绩预告",
                "announcement_date": "2026-05-20",
                "source": "cninfo",
                "source_url": "https://static.cninfo.com.cn/finalpage/2026-05-20/test.PDF",
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "title": "关于召开说明会的公告",
                "category": "其他公告",
                "announcement_date": "2026-05-18",
                "source": "cninfo",
                "source_url": "https://static.cninfo.com.cn/finalpage/2026-05-18/test.PDF",
            },
        ],
        "missing_stock_codes": [],
    }
