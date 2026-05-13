# Parent Decision

## Decision

Use parent execution for the V1 mock pipeline implementation.

## Rationale

The task is multi-file and qualifies for ECC run tracking, but the current Codex tool policy only allows child agents when the user explicitly requests delegated or parallel agent work. The implementation will still follow the run directory, TDD, verification, and quality-recording discipline.

## Branch

- Branch: `codex/v1-mock-pipeline`
- Base commit: `fde4c44fc5af54ffed5b1c1a942d98bc35094c80`
- Worktree: main workspace

## Scope Control

V1 remains mock-provider first, no real API credentials, no LLM dependency, no buy/sell signals.
