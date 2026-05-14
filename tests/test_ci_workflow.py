from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_github_actions_ci_runs_standard_quality_gates():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "python -m pip install -e \".[dev]\"" in workflow
    assert "python -m ruff check ." in workflow
    assert "python scripts/validate_v1_acceptance.py" in workflow
    assert "python -m coverage run -m pytest -q" in workflow
    assert "python -m coverage report" in workflow
    assert "python -m compileall -q src tests scripts" in workflow
