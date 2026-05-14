import json
import subprocess
import sys

import pytest
from scripts import validate_v1_acceptance


def test_validate_v1_acceptance_script_passes_with_explicit_output_dir(
    tmp_path,
    capsys,
):
    exit_code = validate_v1_acceptance.main(["--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "V1 acceptance passed:" in captured.out
    assert str(tmp_path) in captured.out
    assert (tmp_path / "fund_000001_manifest.json").exists()
    assert (tmp_path / "fund_000001_review_queue.json").exists()


def test_validate_v1_acceptance_script_runs_as_file(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_v1_acceptance.py",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "V1 acceptance passed:" in result.stdout


def test_validate_acceptance_outputs_rejects_missing_mock_source_url(tmp_path):
    output_dir = tmp_path
    output_dir.mkdir(exist_ok=True)
    raw_path = output_dir / "fund_000001_raw.json"
    scoring_path = output_dir / "fund_000001_scoring.json"
    manifest_path = output_dir / "fund_000001_manifest.json"
    review_queue_path = output_dir / "fund_000001_review_queue.json"
    markdown_path = output_dir / "fund_000001_report.md"
    html_path = output_dir / "fund_000001_report.html"

    raw_path.write_text(
        json.dumps(
            {
                "metadata": {"fund_code": "000001", "data_quality": "mock"},
                "fund": {
                    "provider_metadata": {
                        "source_url": None,
                        "data_quality": "mock",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    scoring_path.write_text(
        json.dumps(
            {
                "metadata": {"fund_code": "000001", "data_quality": "mock"},
                "provider_foundation": {
                    "effective_data_quality": "mock",
                    "layers": {
                        "holdings": {
                            "source_url": None,
                            "is_mock": True,
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "version": "pipeline-artifact-manifest-v1",
                "fund_code": "000001",
                "web_ready": True,
            }
        ),
        encoding="utf-8",
    )
    review_queue_path.write_text(
        json.dumps({"candidate_review_queue": {"version": "candidate-review-queue-v1"}}),
        encoding="utf-8",
    )
    markdown_path.write_text("Data Source Notice\nMock 数据\n", encoding="utf-8")
    html_path.write_text("Data Source Notice\nMock 数据\n", encoding="utf-8")

    with pytest.raises(validate_v1_acceptance.AcceptanceError) as exc:
        validate_v1_acceptance.validate_acceptance_outputs(output_dir)

    assert "raw fund provider source_url must disclose mock fixture" in str(exc.value)
