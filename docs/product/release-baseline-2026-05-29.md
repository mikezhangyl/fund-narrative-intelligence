# Release Baseline - 2026-05-29

Linear issues: `MIK-53`, `MIK-61`

## Decision

The PM/Architect-accepted branch `codex/linear-fni-develop` was merged into
`main` using a fast-forward merge, then pushed to `origin/main`.

Future implementation work starts from `main`; `codex/linear-fni-develop`
remains only as historical release evidence.

## Baseline Commits

- Pre-merge `main`: `f22503ed59bafcecb4ac14223aac6d7a2d99627c`
- Accepted branch head: `09c174d545c64ad97696abd5dc57c4cfc528f22f`
- Post-merge `origin/main`: `09c174d545c64ad97696abd5dc57c4cfc528f22f`
- MIK-51 fix: `74230a8 fix: bootstrap narrative review workspace cli`
- Acceptance update: `09c174d docs: accept linear fni branch after rereview`

## Merge Protocol

- Merge type: fast-forward.
- Source branch: `codex/linear-fni-develop`.
- Destination branch: `main`.
- Remote destination: `origin/main`.
- Generated acceptance outputs under `outputs/` remain ignored artifacts and
  were not committed as release source.
- Durable ECC run artifacts under `.ecc/runs/` were preserved in the merge.

## Acceptance Reference

PM/Architect acceptance is recorded in:

`docs/product/pm-architect-acceptance-review-2026-05-29.md`

That document preserves the original blocker and appends the re-review decision:
`accepted for merge`.

## Verification Evidence

Pre-merge and post-merge verification covered:

```bash
uv run ruff check .
uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests
uv run pytest -q
uv run python scripts/validate_stock_narrative_service_acceptance.py
git diff --check main...HEAD
git status --short --branch
```

Observed release results:

```text
pytest: 520 passed, 1 skipped
Narrative Service acceptance: status=completed
provider_smoke_source=narrative_service
fallback_smoke_source=local_prototype
report_narrative_source=narrative_service
pre-push hook: 520 passed, 1 skipped
main: clean and synced to origin/main after push
```

## Caveats

- live gateway/provider checks were not used as merge blockers.
- The deterministic acceptance harness separates local contract checks from live
  gateway/provider checks.
- Round 2 live validation will classify live gateway and Narrative Service
  behavior separately from this release baseline.

## Future Work Pointer

New Round 2 and Round 3 development must use `main` / `origin/main` as the stable
baseline, not the long-lived `codex/linear-fni-develop` branch.
