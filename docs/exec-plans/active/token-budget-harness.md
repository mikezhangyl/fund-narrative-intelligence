# Token Budget Harness Optimization

## Goal

Reduce unnecessary token use in future development sessions by making project context summary-first, path-based, and task-selected.

## Scope

- Thin default startup context in `AGENTS.md`.
- Add short memory entry points under `docs/memory/`.
- Keep full memory and ADR files as on-demand references.
- Curate `docs/exec-plans/active/index.md` so it is an active queue, not a historical catalog.
- Add a deterministic context loader script.
- Update project-local skills that control bootstrap and memory behavior.

## Out Of Scope

- Changing product runtime behavior.
- Moving or deleting historical run artifacts.
- Editing files outside this repository.
- Rewriting unrelated provider, report, registry, or test logic.

## Acceptance

- Default startup files are under roughly 3,000 words combined.
- `python scripts/context_brief.py --max-words 900` emits a bounded context view.
- Context loader has focused tests.
- Harness docs clearly say full memory, full ADRs, all plans, and all runs are on-demand only.
- Existing development workflow remains usable.

## Verification

- `python -m pytest tests/test_context_brief.py -q`
- `python -m ruff check scripts/context_brief.py tests/test_context_brief.py`
- `python -m py_compile scripts/context_brief.py scripts/ecc_task_run.py scripts/qa_test_run.py`
- `python scripts/context_brief.py --max-words 900`
- `wc -w AGENTS.md docs/memory/current-brief.md docs/memory/architecture-decisions.index.md docs/exec-plans/active/index.md skills/ecc-task-subagent-workflow/SKILL.md skills/project-bootstrap/SKILL.md skills/memory-governance/SKILL.md`
