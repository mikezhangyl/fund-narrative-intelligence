# Validate Review Queue CLI Execution Plan

## Goal

Expose a direct CLI validator for `fund_<code>_review_queue.json` so future web approval screens can trust the queue artifact contract without running the full fund pipeline.

## Scope

- Add a reusable review queue artifact validator.
- Add `python -m src.main --validate-review-queue path/to/review_queue.json`.
- Cover valid generated artifacts and malformed payload rejection in tests.
- Update project docs and memory.

## Non-Goals

- No web UI.
- No review action persistence changes.
- No registry mutation.

## Acceptance

- Generated review queue artifacts validate from the CLI.
- Malformed queue artifacts fail fast with a clear contract error.
- Full lint, compile, coverage, and smoke checks pass.
