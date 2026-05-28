# ECC Operating Mode

This project uses a merged ECC framework:

- ECC's project-local skills, rules, quality discipline, and development workflow.
- Superpower-inspired execution discipline: explicit plans, canonical run directories, worktree criteria, fresh review, and finish-branch decisions.
- Project memory as durable files, not chat memory.

## Startup Context

Default startup is token-light. Before routine project work, read only:

1. `.ecc/framework-state.json`
2. `docs/memory/operating-rules.md`
3. `docs/memory/current-brief.md`
4. `docs/memory/architecture-decisions.index.md`
5. `docs/exec-plans/active/index.md`
6. newest relevant `.ecc/runs/<task-run-id>/run-state.json`, only when continuing a known run
7. any task-specific skill named by the user or clearly implied by the task

For a compact generated view, run:

```bash
python scripts/context_brief.py --max-words 900
```

Do not load `docs/memory/project-context.md`, `docs/memory/architecture-decisions.md`, all active plans, or all `.ecc/runs/**` by default. Open heavier context only when the task requires full history, exact architecture rationale, a named plan, or a specific run artifact.

`default_skills` and `library_skills` in `.ecc/framework-state.json` are project-local harness metadata, not a Codex native autoload mechanism. Treat `default_skills` as the startup skill set and `library_skills` as installed, available, on-demand skills.

## Default Workflow

Use parent execution for small or unclear tasks. When the next step is clear,
execute directly instead of asking for permission. Stop to ask only when a
required decision cannot be inferred safely, credentials or external access are
missing, or the action is destructive or high risk.

For complex implementation, framework, or PR-bound tasks:

1. Create or continue a plan under `docs/exec-plans/active/`.
2. Create one canonical `.ecc/runs/<task-run-id>/`.
3. Use exactly one owning Task Agent only when the task qualifies.
4. Do not start nested or same-task role agents after `task_run_id` exists.
5. Run Quality Agent review after implementation when risk warrants it.
6. Record artifacts, findings, decisions, and final disposition in the same run directory.
7. Distill durable knowledge into `docs/memory/` and `.ecc/memory/project/`.

## Agent Policy

- Parent Orchestrator owns all agent starts.
- Task Agent never spawns child agents.
- Quality Agent reviews and writes findings, but does not fix product code.
- Role specialists may be used before a task run exists for planning or scoping.
- Once `task_run_id` exists, same-task role-agent fanout is forbidden.

## Worktree Policy

Default: do not create a worktree.

Create a worktree only for multi-file implementation, risky shared behavior, autonomous workflow changes, parallel work, long-running work, or PR-bound work. Record branch, base commit, head commit, merge base, and final disposition in `.ecc/runs/<task-run-id>/run-state.json`.

## Memory Policy

- Operating rules: `docs/memory/operating-rules.md`
- Startup memory: `docs/memory/current-brief.md` and `docs/memory/architecture-decisions.index.md`
- Full project facts and decisions: `docs/memory/`
- Machine-readable/current framework state: `.ecc/framework-state.json`
- Run-specific temporary state: `.ecc/runs/<task-run-id>/`
- Reusable project memory snippets: `.ecc/memory/project/`
- General cross-project heuristics: `.ecc/memory/global/`
- Do not store secrets, private credentials, or raw sensitive data in memory files.
- Keep startup memory short; move details into full memory files and link to them.

## Token Budget Policy

- Parent execution is the default for small tasks.
- Do not scan `docs/exec-plans/active/*.md` or `.ecc/runs/**` unless the task names those artifacts or requires history.
- Read full ADRs only by ADR number or keyword.
- Trigger `ecc-task-subagent-workflow` only for large, risky, long-running, autonomous, parallel, or PR-bound work.
- Prefer one concise task-local handoff over replaying chat history.

## Report Policy

All formal reader-facing reports must include Chinese HTML output as the
canonical readable artifact. JSON remains machine-readable. Markdown may exist
only as auxiliary compatibility output and must not be the formal reading
surface for new reports. Each formal metric should explain its meaning and
expose data source / 口径 details through hover/tooltips where practical.

## Chat Boundary Policy

Use one chat per coherent work slice. Tell the user a new chat boundary has been
reached when the goal moves to a different deliverable, the relevant modules no
longer overlap, the work mode changes between implementation/review/architecture
discussion/provider research, or the current thread has enough history that old
assumptions are likely to interfere.

Before asking for a new chat, write durable state into project files if needed,
then provide a short handoff with goal, branch, relevant files, verification
state, and unresolved risks.

## Finish Policy

After a feature slice has passed verification and before starting a different
feature slice, check `git status` and create a checkpoint commit for the
completed work unless the user explicitly asks to leave it uncommitted. "Keep
going" means continue with the next task after the appropriate checkpoint, not
skip git/ECC finish discipline.

Before closing a branch or worktree, record final commit, review status,
artifact locations, and the keep / merge / PR / discard decision.

## Optional Libraries

QA and black-box testing skills may exist under `skills/` as optional library skills. They are not the default operating mode for this project unless the user asks for QA/testing work.
