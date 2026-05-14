import pytest
from src import main as main_module
from src.errors import ProviderFetchError


def test_main_lists_fixtures(capsys):
    exit_code = main_module.main(["--list-fixtures"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "000001" in captured.out


def test_main_run_all_fixtures_prints_artifacts(tmp_path, capsys):
    exit_code = main_module.main(
        ["--run-all-fixtures", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Generated fixture artifacts:" in captured.out
    assert "000003" in captured.out


def test_main_requires_fund_code_when_no_batch_flag():
    with pytest.raises(SystemExit) as exc:
        main_module.main([])

    assert exc.value.code == 2


def test_main_returns_controlled_error_for_missing_fixture(tmp_path, capsys):
    exit_code = main_module.main(
        ["--fund-code", "999999", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No mock fixture found for fund code 999999" in captured.err


def test_main_rejects_invalid_fund_code(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main_module.main(["--fund-code", "ABC", "--output-dir", str(tmp_path)])

    assert exc.value.code == 2


def test_main_run_real_smoke_returns_status(monkeypatch, tmp_path, capsys):
    def fake_run_real_fund_smoke(output_dir):
        assert output_dir == str(tmp_path)
        return {
            "status": "passed",
            "funds": [
                {
                    "fund_code": "161725",
                    "scenario": "baijiu_consumption",
                    "primary_narrative": "Premium Baijiu Consumption",
                    "stage": "diverging",
                    "coverage_ratio": 1.0,
                    "mapping_precision_flag_count": 2,
                    "excluded_mapping_candidate_count": 1,
                    "candidate_narrative_count": 1,
                }
            ],
        }

    monkeypatch.setattr(
        main_module, "run_real_fund_smoke", fake_run_real_fund_smoke
    )

    exit_code = main_module.main(
        ["--run-real-smoke", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "status=passed" in captured.out
    assert "coverage=100%" in captured.out
    assert "precision_flags=2" in captured.out
    assert "excluded_candidates=1" in captured.out
    assert "candidate_narratives=1" in captured.out


def test_main_run_real_smoke_returns_nonzero_for_failed_summary(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        main_module,
        "run_real_fund_smoke",
        lambda output_dir: {"status": "failed", "funds": []},
    )

    exit_code = main_module.main(
        ["--run-real-smoke", "--output-dir", str(tmp_path)]
    )

    assert exit_code == 1


def test_main_run_real_smoke_handles_controlled_error(monkeypatch, capsys):
    def failing_run_real_fund_smoke(output_dir):
        raise ProviderFetchError("provider unavailable")

    monkeypatch.setattr(
        main_module, "run_real_fund_smoke", failing_run_real_fund_smoke
    )

    exit_code = main_module.main(["--run-real-smoke"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "provider unavailable" in captured.err


def test_main_run_announcement_smoke_returns_status(monkeypatch, tmp_path, capsys):
    def fake_run_announcement_evidence_smoke(output_dir):
        assert output_dir == str(tmp_path)
        return {
            "status": "passed",
            "cases": [
                {
                    "fund_code": "161725",
                    "scenario": "baijiu_cninfo_metadata",
                    "announcement_count": 56,
                    "announcement_evidence_count": 56,
                    "data_source_notice_required": True,
                    "effective_data_quality": "partial",
                }
            ],
        }

    monkeypatch.setattr(
        main_module,
        "run_announcement_evidence_smoke",
        fake_run_announcement_evidence_smoke,
    )

    exit_code = main_module.main(
        ["--run-announcement-smoke", "--output-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Announcement evidence smoke summary:" in captured.out
    assert "status=passed" in captured.out
    assert "161725 baijiu_cninfo_metadata announcements=56 evidence=56" in captured.out


def test_main_run_announcement_smoke_returns_nonzero_for_failed_summary(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        main_module,
        "run_announcement_evidence_smoke",
        lambda output_dir: {"status": "failed", "cases": []},
    )

    exit_code = main_module.main(
        ["--run-announcement-smoke", "--output-dir", str(tmp_path)]
    )

    assert exit_code == 1
