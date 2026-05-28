from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_developer_ready_linear_handoff_format_is_documented():
    document = PROJECT_ROOT / "docs" / "product" / "developer-ready-linear-handoff-format.md"
    text = document.read_text(encoding="utf-8")

    required_headings = [
        "## Required Issue Sections",
        "## Handoff Template",
        "## Next-Issue Selection",
        "## Checkpoint And Completion",
        "## Verification Commands",
    ]
    for heading in required_headings:
        assert heading in text

    required_fields = [
        "Product intent",
        "Scope",
        "Non-goals",
        "Architecture constraints",
        "Dependencies",
        "Acceptance criteria",
        "Verification commands",
    ]
    for field in required_fields:
        assert field in text

    assert "highest-priority Todo issue in milestone order" in text
    assert "checkpoint commit" in text
    assert "Linear completion comment" in text


def test_current_brief_points_developers_to_handoff_format():
    current_brief = (PROJECT_ROOT / "docs" / "memory" / "current-brief.md").read_text(
        encoding="utf-8"
    )

    assert "developer-ready-linear-handoff-format.md" in current_brief
