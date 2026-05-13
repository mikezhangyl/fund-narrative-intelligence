import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())


def test_pyproject_declares_reproducible_dev_tooling():
    config = _load_pyproject()

    dev_dependencies = config["project"]["optional-dependencies"]["dev"]

    assert "pytest==8.3.4" in dev_dependencies
    assert "ruff==0.15.12" in dev_dependencies
    assert "coverage[toml]==7.14.0" in dev_dependencies


def test_pyproject_configures_lint_and_coverage_gates():
    config = _load_pyproject()

    assert config["tool"]["pytest"]["ini_options"]["pythonpath"] == ["."]
    assert config["tool"]["ruff"]["target-version"] == "py311"
    assert "src" in config["tool"]["ruff"]["src"]
    assert config["tool"]["coverage"]["run"]["branch"] is True
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 80


def test_readme_documents_standard_quality_commands():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert 'python -m pip install -e ".[dev]"' in readme
    assert "python -m ruff check ." in readme
    assert "python -m coverage run -m pytest -q" in readme
    assert "python -m coverage report\n" in readme
    assert "coverage report --fail-under" not in readme
