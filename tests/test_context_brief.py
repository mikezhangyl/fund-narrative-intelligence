from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_context_brief_respects_word_budget(tmp_path: Path) -> None:
    _write_minimal_context(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/context_brief.py",
            "--root",
            str(tmp_path),
            "--max-words",
            "80",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# Context Brief" in result.stdout
    assert "Operating Rules" in result.stdout
    assert "startup_profile" in result.stdout
    assert "default_skills" in result.stdout
    assert "library_skills_on_demand" in result.stdout
    assert len(result.stdout.split()) <= 82
    assert "full project context that should stay out of default startup" not in result.stdout


def test_context_brief_json_lists_default_context_files(tmp_path: Path) -> None:
    _write_minimal_context(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/context_brief.py",
            "--root",
            str(tmp_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["framework_state"]["framework"] == "test-framework"
    assert "docs/memory/operating-rules.md" in payload["default_context_files"]
    assert "docs/memory/current-brief.md" in payload["default_context_files"]
    assert payload["active_plans"] == [{"title": "current-plan.md", "path": "./current-plan.md"}]
    assert payload["recent_runs"][0]["run_id"] == "run-1"


def _write_minimal_context(root: Path) -> None:
    (root / ".ecc" / "runs" / "run-1").mkdir(parents=True)
    (root / "docs" / "memory").mkdir(parents=True)
    (root / "docs" / "exec-plans" / "active").mkdir(parents=True)

    (root / ".ecc" / "framework-state.json").write_text(
        json.dumps(
            {
                "framework": "test-framework",
                "default_skills": ["project-bootstrap"],
                "library_skills": ["memory-governance"],
                "current_phase": "test",
                "latest_run": "run-1",
                "next_step": "continue",
                "context_policy": {"startup_profile": "token_light"},
            }
        ),
        encoding="utf-8",
    )
    (root / ".ecc" / "runs" / "run-1" / "run-state.json").write_text(
        json.dumps(
            {
                "task_run_id": "run-1",
                "task_state": "passed",
                "task_type": "implementation",
                "review_outcome": "done",
            }
        ),
        encoding="utf-8",
    )
    (root / "docs" / "memory" / "current-brief.md").write_text(
        "# Current Brief\n\nShort summary only.\n",
        encoding="utf-8",
    )
    (root / "docs" / "memory" / "operating-rules.md").write_text(
        "# Operating Rules\n\nUse parent execution for small tasks.\n",
        encoding="utf-8",
    )
    (root / "docs" / "memory" / "architecture-decisions.index.md").write_text(
        "# Architecture Decisions Index\n\nADR-0001 summary.\n",
        encoding="utf-8",
    )
    (root / "docs" / "memory" / "project-context.md").write_text(
        "full project context that should stay out of default startup\n" * 100,
        encoding="utf-8",
    )
    (root / "docs" / "exec-plans" / "active" / "index.md").write_text(
        "# Active Execution Plans\n\n- [current-plan.md](./current-plan.md)\n",
        encoding="utf-8",
    )
