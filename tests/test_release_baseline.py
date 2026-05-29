from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_round2_release_baseline_records_merge_protocol_and_acceptance():
    document = PROJECT_ROOT / "docs" / "product" / "release-baseline-2026-05-29.md"
    text = document.read_text(encoding="utf-8")

    required_terms = [
        "MIK-53",
        "MIK-61",
        "codex/linear-fni-develop",
        "origin/main",
        "fast-forward",
        "09c174d545c64ad97696abd5dc57c4cfc528f22f",
        "docs/product/pm-architect-acceptance-review-2026-05-29.md",
        "520 passed, 1 skipped",
        "uv run ruff check .",
        "uv run python -m compileall -q",
        "uv run python scripts/validate_stock_narrative_service_acceptance.py",
        "live gateway/provider checks",
        "main",
    ]
    for term in required_terms:
        assert term in text


def test_round2_execution_plan_points_future_work_to_main_baseline():
    plan = (
        PROJECT_ROOT
        / "docs"
        / "exec-plans"
        / "active"
        / "round2-round3-linear-execution.md"
    ).read_text(encoding="utf-8")

    assert "release-baseline-2026-05-29.md" in plan
    assert "Future implementation work starts from `main`" in plan
