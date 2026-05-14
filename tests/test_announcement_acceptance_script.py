import json
from pathlib import Path

import pytest
from scripts import validate_announcement_acceptance


def test_announcement_acceptance_script_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_announcement_outputs(tmp_path)
        return 0

    monkeypatch.setattr(validate_announcement_acceptance.pipeline_main, "main", fake_main)

    exit_code = validate_announcement_acceptance.main(["--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Announcement acceptance passed:" in captured.out
    assert calls == [
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-cninfo-announcements",
            "--announcement-start-date",
            "2026-01-01",
            "--output-dir",
            str(tmp_path),
        ],
        ["--validate-artifact-contracts", str(tmp_path)],
    ]


def test_announcement_acceptance_rejects_missing_cninfo_evidence(tmp_path):
    _write_announcement_outputs(tmp_path, announcement_count=2, evidence_count=0)

    with pytest.raises(validate_announcement_acceptance.AcceptanceError) as exc:
        validate_announcement_acceptance.validate_acceptance_outputs(tmp_path)

    assert "announcement evidence count must be at least 1" in str(exc.value)


def _write_announcement_outputs(
    output_dir: Path,
    announcement_count: int = 2,
    evidence_count: int = 2,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_foundation = {
        "effective_data_quality": "partial",
        "disclosure_required": True,
        "disclosure_message": (
            "混合数据源：Holdings 来自 Eastmoney；Announcements 来自 CNINFO；"
            "Evidence 使用 Mock fixtures。请勿将该报告视为完整真实环境输出。"
        ),
        "layers": {
            "holdings": {
                "layer": "holdings",
                "display_name": "Holdings",
                "provider_name": "eastmoney-fundmobapi",
                "provider_version": "eastmoney-v1",
                "data_quality": "fresh",
                "source_url": (
                    "https://fundmobapi.eastmoney.com/FundMNewApi/"
                    "FundMNInverstPosition?FCODE=161725"
                ),
                "is_mock": False,
                "note": "Fund holdings fetched from Eastmoney.",
            },
            "narrative_registry": _mock_layer("narrative_registry"),
            "stock_mappings": _mock_layer("stock_mappings"),
            "evidence": _mock_layer("evidence"),
            "signals": _mock_layer("signals"),
            "derived_signals": {
                "layer": "derived_signals",
                "display_name": "Derived Signals",
                "provider_name": "cninfo-derived-signals",
                "provider_version": "announcement-derived-signals-v1",
                "data_quality": "fresh",
                "source_url": "derived://cninfo-announcement-evidence",
                "is_mock": False,
                "note": "Derived from CNINFO announcement evidence metadata.",
            },
            "announcements": {
                "layer": "announcements",
                "display_name": "Announcements",
                "provider_name": "cninfo-announcement",
                "provider_version": "cninfo-announcement-v1",
                "data_quality": "fresh",
                "source_url": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
                "is_mock": False,
                "note": "Optional announcement metadata provider.",
            },
        },
        "degradation_events": [],
    }
    announcements = [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "title": f"重大事项公告 {index}",
            "announcement_date": "2026-03-15",
            "source_url": "https://static.cninfo.com.cn/fake.pdf",
        }
        for index in range(announcement_count)
    ]
    evidence = [
        {
            "evidence_id": f"cninfo-600519-{index}",
            "narrative_id": "premium_baijiu_consumption",
            "source": "cninfo_announcement",
            "source_url": "https://static.cninfo.com.cn/fake.pdf",
            "summary": "CNINFO announcement metadata.",
            "sentiment": "mixed",
        }
        for index in range(evidence_count)
    ]
    derived_signal_events = [
        {
            "signal_id": f"SIG_ANN_cninfo-600519-{index}",
            "narrative_id": "premium_baijiu_consumption",
            "signal_type": "management_mentions_up",
            "strength": 0.18,
            "confidence": 0.3,
            "confidence_multiplier": 0.55,
            "event_date": "2026-03-15",
            "half_life_days": 30,
            "source": "cninfo_announcement",
            "source_evidence_id": f"cninfo-600519-{index}",
            "source_url": "https://static.cninfo.com.cn/fake.pdf",
            "derivation_reason": "mixed financial disclosure announcement evidence",
        }
        for index in range(evidence_count)
    ]
    raw = {
        "metadata": {
            "fund_code": "161725",
            "as_of_date": "2026-03-31",
            "data_quality": "partial",
        },
        "fund": {
            "fund_code": "161725",
            "provider_metadata": {
                "provider_name": "eastmoney-fundmobapi",
                "provider_version": "eastmoney-v1",
                "data_quality": "fresh",
                "source_url": (
                    "https://fundmobapi.eastmoney.com/FundMNewApi/"
                    "FundMNInverstPosition?FCODE=161725"
                ),
            },
        },
        "provider_foundation": provider_foundation,
        "announcements": {
            "version": "cninfo-announcement-v1",
            "data_quality": "fresh",
            "announcements": announcements,
            "missing_stock_codes": [],
        },
        "announcement_evidence": {
            "version": "announcement-evidence-v1",
            "data_quality": "fresh",
            "evidence": evidence,
            "skipped_announcement_count": 0,
        },
        "evidence": evidence,
        "signal_events": derived_signal_events,
        "derived_signal_events": derived_signal_events,
        "degradation_events": [],
    }
    scoring = {
        "metadata": raw["metadata"],
        "fund": raw["fund"],
        "provider_foundation": provider_foundation,
        "announcement_evidence": raw["announcement_evidence"],
        "derived_signal_events": derived_signal_events,
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {"total_count": 0, "pending_count": 0, "action_required": False},
            "items": [],
        },
        "degradation_events": [],
    }
    review_queue = {
        "metadata": raw["metadata"],
        "fund": raw["fund"],
        "provider_foundation": provider_foundation,
        "candidate_review_queue": scoring["candidate_review_queue"],
        "candidate_narratives": [],
        "excluded_mapping_candidates": [],
    }
    source_table = {
        "version": "source-table-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_foundation": provider_foundation,
        "layers": list(provider_foundation["layers"].values()),
        "degradation_events": provider_foundation["degradation_events"],
    }
    manifest = {
        "version": "pipeline-artifact-manifest-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_mode": "eastmoney",
        "data_quality": "partial",
        "web_ready": True,
        "provider_foundation": provider_foundation,
        "degradation_events": [],
        "artifacts": {
            "raw": {"path": "fund_161725_raw.json", "format": "json"},
            "scoring": {"path": "fund_161725_scoring.json", "format": "json"},
            "review_queue": {
                "path": "fund_161725_review_queue.json",
                "format": "json",
            },
            "source_table": {
                "path": "fund_161725_source_table.json",
                "format": "json",
            },
            "markdown": {"path": "fund_161725_report.md", "format": "markdown"},
            "html": {"path": "fund_161725_report.html", "format": "html"},
        },
    }

    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_review_queue.json", review_queue)
    _write_json(output_dir / "fund_161725_source_table.json", source_table)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    (output_dir / "fund_161725_report.md").write_text(
        "Data Source Notice\n混合数据源\nEastmoney\nCNINFO\nMock fixtures\n",
        encoding="utf-8",
    )
    (output_dir / "fund_161725_report.html").write_text(
        "Data Source Notice\n混合数据源\nEastmoney\nCNINFO\nMock fixtures\n",
        encoding="utf-8",
    )


def _mock_layer(layer: str) -> dict:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": "mock-fixture-provider",
        "provider_version": "mock-v1",
        "data_quality": "mock",
        "source_url": f"mock://fixtures/{layer}.json",
        "is_mock": True,
        "note": "V1 Mock fixture layer.",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
