from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLAN_LINK_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\)", re.MULTILINE)


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    state: str | None
    task_type: str | None
    outcome: str | None
    path: str


def build_context_brief(
    root: Path,
    *,
    max_words: int,
    max_active_plans: int,
    max_runs: int,
) -> str:
    framework_state = _read_json(root / ".ecc" / "framework-state.json")
    current_brief = _read_text(root / "docs" / "memory" / "current-brief.md")
    operating_rules = _read_text(root / "docs" / "memory" / "operating-rules.md")
    adr_index = _read_text(root / "docs" / "memory" / "architecture-decisions.index.md")
    active_index = _read_text(root / "docs" / "exec-plans" / "active" / "index.md")
    active_plans = _extract_plan_links(active_index)[:max_active_plans]
    recent_runs = _recent_runs(root / ".ecc" / "runs", max_runs=max_runs)

    sections = [
        "# Context Brief",
        _format_framework_state(framework_state),
        "## Operating Rules",
        _first_nonempty_lines(_strip_heading(operating_rules), max_lines=20),
        "## Default Memory",
        _strip_heading(current_brief),
        "## ADR Index",
        _first_nonempty_lines(_strip_heading(adr_index), max_lines=18),
        "## Active Plans",
        _format_active_plans(active_plans),
        "## Recent Runs",
        _format_runs(recent_runs),
        "## Heavy Context On Demand",
        "\n".join(
            [
                "- Full project facts: docs/memory/project-context.md",
                "- Full ADR bodies: docs/memory/architecture-decisions.md",
                "- Specific plan bodies: docs/exec-plans/active/<plan>.md",
                "- Historical run artifacts: .ecc/runs/<task-run-id>/",
            ]
        ),
    ]
    return _trim_words("\n\n".join(section for section in sections if section.strip()), max_words)


def build_context_json(root: Path, *, max_active_plans: int, max_runs: int) -> dict[str, Any]:
    framework_state = _read_json(root / ".ecc" / "framework-state.json")
    active_index = _read_text(root / "docs" / "exec-plans" / "active" / "index.md")
    return {
        "framework_state": framework_state,
        "default_context_files": [
            ".ecc/framework-state.json",
            "docs/memory/operating-rules.md",
            "docs/memory/current-brief.md",
            "docs/memory/architecture-decisions.index.md",
            "docs/exec-plans/active/index.md",
        ],
        "active_plans": [
            {"title": title, "path": path}
            for title, path in _extract_plan_links(active_index)[:max_active_plans]
        ],
        "recent_runs": [run.__dict__ for run in _recent_runs(root / ".ecc" / "runs", max_runs=max_runs)],
        "heavy_context_on_demand": [
            "docs/memory/project-context.md",
            "docs/memory/architecture-decisions.md",
            "docs/exec-plans/active/<plan>.md",
            ".ecc/runs/<task-run-id>/",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Print token-light project context.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--max-words", type=int, default=900)
    parser.add_argument("--max-active-plans", type=int, default=6)
    parser.add_argument("--max-runs", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.as_json:
        print(json.dumps(build_context_json(root, max_active_plans=args.max_active_plans, max_runs=args.max_runs), ensure_ascii=False, indent=2))
    else:
        print(
            build_context_brief(
                root,
                max_words=args.max_words,
                max_active_plans=args.max_active_plans,
                max_runs=args.max_runs,
            )
        )
    return 0


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _format_framework_state(state: dict[str, Any]) -> str:
    if not state:
        return "## Framework\n\nNo framework state found."
    lines = [
        "## Framework",
        f"- framework: {state.get('framework', 'unknown')}",
        f"- default_skills: {_format_list(state.get('default_skills'))}",
        f"- library_skills_on_demand: {_format_list(state.get('library_skills'))}",
        f"- current_phase: {state.get('current_phase', 'unknown')}",
        f"- latest_run: {state.get('latest_run', 'unknown')}",
        f"- next_step: {state.get('next_step', 'unknown')}",
    ]
    context_policy = state.get("context_policy")
    if isinstance(context_policy, dict):
        lines.append(f"- startup_profile: {context_policy.get('startup_profile', 'unknown')}")
    return "\n".join(lines)


def _extract_plan_links(markdown: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2)) for match in PLAN_LINK_RE.finditer(markdown)]


def _recent_runs(runs_dir: Path, *, max_runs: int) -> list[RunSummary]:
    if not runs_dir.exists():
        return []
    states = sorted(
        runs_dir.glob("*/run-state.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    summaries: list[RunSummary] = []
    for path in states[:max_runs]:
        payload = _read_json(path)
        summaries.append(
            RunSummary(
                run_id=str(payload.get("task_run_id") or path.parent.name),
                state=payload.get("task_state"),
                task_type=payload.get("task_type"),
                outcome=_trim_words(str(payload.get("review_outcome") or ""), 28),
                path=str(path.relative_to(runs_dir.parent.parent)),
            )
        )
    return summaries


def _format_active_plans(plans: list[tuple[str, str]]) -> str:
    if not plans:
        return "No active plans listed."
    return "\n".join(f"- {title}: {path}" for title, path in plans)


def _format_list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(str(item) for item in value)


def _format_runs(runs: list[RunSummary]) -> str:
    if not runs:
        return "No run-state files found."
    lines = []
    for run in runs:
        outcome = f" - {run.outcome}" if run.outcome else ""
        lines.append(f"- {run.run_id}: {run.state} / {run.task_type}{outcome}")
    return "\n".join(lines)


def _strip_heading(markdown: str) -> str:
    lines = markdown.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return markdown.strip()


def _first_nonempty_lines(text: str, *, max_lines: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "\n\n[truncated]"


if __name__ == "__main__":
    raise SystemExit(main())
