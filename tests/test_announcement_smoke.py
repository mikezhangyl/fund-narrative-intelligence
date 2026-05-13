import json
from pathlib import Path

from src.announcement_smoke import (
    ANNOUNCEMENT_EVIDENCE_SMOKE_SET,
    run_announcement_evidence_smoke,
)
from src.errors import ProviderFetchError


def test_announcement_evidence_smoke_set_uses_real_a_share_fund():
    assert ANNOUNCEMENT_EVIDENCE_SMOKE_SET == [
        {
            "fund_code": "161725",
            "scenario": "baijiu_cninfo_metadata",
            "provider_mode": "eastmoney",
            "announcement_start_date": "2026-01-01",
            "min_announcement_count": 1,
        }
    ]


def test_announcement_evidence_smoke_passes_with_announcements_and_notice(tmp_path):
    def fake_runner(
        fund_code: str,
        provider_mode: str,
        output_dir: Path,
        include_announcement_evidence: bool,
        announcement_start_date: str,
    ):
        assert fund_code == "161725"
        assert provider_mode == "eastmoney"
        assert include_announcement_evidence is True
        assert announcement_start_date == "2026-01-01"
        raw_path = output_dir / f"fund_{fund_code}_raw.json"
        scoring_path = output_dir / f"fund_{fund_code}_scoring.json"
        markdown_path = output_dir / f"fund_{fund_code}_report.md"
        html_path = output_dir / f"fund_{fund_code}_report.html"
        raw_path.write_text(
            json.dumps(
                {
                    "metadata": {"as_of_date": "2026-03-31"},
                    "announcements": {
                        "data_quality": "fresh",
                        "announcements": [
                            {"stock_code": "600519", "title": "重大事项公告"},
                            {"stock_code": "000858", "title": "董事会公告"},
                        ],
                        "missing_stock_codes": [],
                    },
                    "announcement_evidence": {
                        "data_quality": "fresh",
                        "evidence": [
                            {"source": "cninfo_announcement"},
                            {"source": "cninfo_announcement"},
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        scoring_path.write_text(
            json.dumps(
                {
                    "metadata": {
                        "fund_code": fund_code,
                        "data_quality": "partial",
                        "as_of_date": "2026-03-31",
                    },
                    "provider_foundation": {
                        "effective_data_quality": "partial",
                        "disclosure_required": True,
                        "disclosure_message": (
                            "混合数据源：Holdings 来自 Eastmoney；Announcements 来自 CNINFO；"
                            "Evidence 使用 Mock fixtures。请勿将该报告视为完整真实环境输出。"
                        ),
                        "layers": {
                            "announcements": {
                                "provider_name": "cninfo-announcement",
                                "data_quality": "fresh",
                                "is_mock": False,
                                "source_url": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
                            }
                        },
                    },
                    "degradation_events": [],
                }
            ),
            encoding="utf-8",
        )
        markdown_path.write_text("# report", encoding="utf-8")
        html_path.write_text("<html></html>", encoding="utf-8")
        return {
            "raw": raw_path,
            "scoring": scoring_path,
            "markdown": markdown_path,
            "html": html_path,
        }

    summary = run_announcement_evidence_smoke(
        output_dir=tmp_path,
        runner=fake_runner,
    )

    result = summary["cases"][0]

    assert summary["status"] == "passed"
    assert result["fund_code"] == "161725"
    assert result["announcement_count"] == 2
    assert result["announcement_evidence_count"] == 2
    assert result["announcement_check_passed"] is True
    assert result["notice_check_passed"] is True
    assert result["announcement_provider"] == "cninfo-announcement"
    assert result["data_source_notice_required"] is True
    assert "Mock fixtures" in result["data_source_notice"]
    assert (tmp_path / "announcement_evidence_smoke_summary.json").exists()
    assert (tmp_path / "announcement_evidence_smoke_summary.md").exists()
    assert "Announcement Evidence Smoke Summary" in (
        tmp_path / "announcement_evidence_smoke_summary.md"
    ).read_text(encoding="utf-8")


def test_announcement_evidence_smoke_fails_when_no_announcements(tmp_path):
    def fake_runner(
        fund_code: str,
        provider_mode: str,
        output_dir: Path,
        include_announcement_evidence: bool,
        announcement_start_date: str,
    ):
        raw_path = output_dir / f"fund_{fund_code}_raw.json"
        scoring_path = output_dir / f"fund_{fund_code}_scoring.json"
        raw_path.write_text(
            json.dumps(
                {
                    "metadata": {"as_of_date": "2026-03-31"},
                    "announcements": {
                        "data_quality": "fresh",
                        "announcements": [],
                        "missing_stock_codes": [],
                    },
                    "announcement_evidence": {
                        "data_quality": "fresh",
                        "evidence": [],
                    },
                }
            ),
            encoding="utf-8",
        )
        scoring_path.write_text(
            json.dumps(
                {
                    "metadata": {"fund_code": fund_code, "data_quality": "partial"},
                    "provider_foundation": {
                        "effective_data_quality": "partial",
                        "disclosure_required": True,
                        "disclosure_message": "混合数据源：Evidence 使用 Mock fixtures。",
                        "layers": {
                            "announcements": {
                                "provider_name": "cninfo-announcement",
                                "data_quality": "fresh",
                                "is_mock": False,
                            }
                        },
                    },
                    "degradation_events": [],
                }
            ),
            encoding="utf-8",
        )
        return {"raw": raw_path, "scoring": scoring_path}

    summary = run_announcement_evidence_smoke(
        output_dir=tmp_path,
        runner=fake_runner,
    )

    assert summary["status"] == "failed"
    assert summary["cases"][0]["announcement_check_passed"] is False
    assert summary["cases"][0]["error"] is None


def test_announcement_evidence_smoke_records_runner_failures(tmp_path):
    def failing_runner(
        fund_code: str,
        provider_mode: str,
        output_dir: Path,
        include_announcement_evidence: bool,
        announcement_start_date: str,
    ):
        raise ProviderFetchError(f"temporary provider failure for {fund_code}")

    summary = run_announcement_evidence_smoke(
        output_dir=tmp_path,
        runner=failing_runner,
    )

    assert summary["status"] == "failed"
    assert summary["cases"][0]["status"] == "failed"
    assert summary["cases"][0]["announcement_check_passed"] is False
    assert "temporary provider failure" in summary["cases"][0]["error"]
