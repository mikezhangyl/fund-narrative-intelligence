# Operating Rules

## Default

Use parent execution for small or unclear tasks.

When the next step is clear, execute directly instead of asking for permission.
Only stop to ask when a required decision cannot be inferred safely, credentials
or external access are missing, or the action is destructive or high risk.

## Reports

All formal reader-facing reports must include Chinese HTML output as the
canonical readable artifact. Keep JSON for machine-readable data. Markdown may
exist only as auxiliary compatibility output and should not be the formal
reading surface for new reports.

Each formal report metric should explain its meaning and expose data source /
口径 details through hover/tooltips where practical.

## Complex Tasks

Use `ecc-task-subagent-workflow` when work is multi-file, risky, long-running, autonomous, parallel, or PR-bound.

## Memory

Default memory is summary-first:

- update `docs/memory/current-brief.md` only when a stable fact should be present at startup
- update `docs/memory/architecture-decisions.index.md` when a full ADR becomes operationally relevant
- keep full facts in `docs/memory/project-context.md`
- keep full decisions in `docs/memory/architecture-decisions.md`
- keep reusable agent snippets in `.ecc/memory/project/`

Do not load full memory files by default. Use `python scripts/context_brief.py --max-words 900` for a compact startup view.

## Token Budget

Avoid avoidable context expansion:

- do not open every file under `docs/exec-plans/active/`
- do not scan all `.ecc/runs/**` unless investigating run history
- do not read full ADR bodies unless a task needs exact rationale
- prefer task-specific code search over broad document loading
- keep handoffs concise and path-based

## Chat Boundaries

Use one chat per coherent work slice, not one chat for the whole project.

Open a new chat when any of the following becomes true:

- the goal changes to a different slice, milestone, or deliverable
- the main files or modules no longer overlap with the current task
- the work changes mode between implementation, review, architecture discussion, or provider research
- the current thread has accumulated enough history that old assumptions are likely to interfere with the next task
- a previous slice is complete and the next slice can be resumed from repository files instead of chat memory

Do not open a new chat when:

- the current feature is only partially implemented and the next step depends directly on recent debugging context
- the current validation failures, branch state, or generated artifacts are still the critical path

When a new chat is needed:

- first write durable state into project files if it is not already captured
- then carry only the minimum handoff context: goal, current branch, relevant files, verification state, and unresolved risks
- prefer starting the new chat from repository state rather than summarizing long chat history

The assistant cannot create or switch chats directly. Instead, it should explicitly tell the user when a chat boundary has been reached and provide a short handoff prompt for the next chat.

## Finish

After a feature slice has passed verification and before starting a different
feature slice, check `git status` and create a checkpoint commit for the
completed work unless the user explicitly asks to leave it uncommitted. "Keep
going" means continue with the next task after the appropriate checkpoint, not
skip git/ECC finish discipline.

Before closing a branch or worktree, record:

- final commit
- review status
- artifact locations
- keep / merge / PR / discard decision
