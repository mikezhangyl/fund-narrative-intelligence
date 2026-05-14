# Review Queue Artifact Execution Plan

## Purpose

Create a dedicated review queue artifact so future web approval screens can load review work without parsing raw or scoring snapshots.

## Scope

- Write `fund_<code>_review_queue.json` beside raw/scoring/report artifacts.
- Include the queue and the minimal context needed to render review work.
- Keep the queue read-only and separate from review action persistence.
- Return the review queue artifact path from `run_pipeline`.

## Non-Goals

- Building web UI.
- Persisting review decisions.
- Removing queue data from raw/scoring JSON.

## Acceptance

- Pipeline returns a `review_queue` artifact path.
- Artifact payload contains metadata, fund, provider foundation, queue, candidate narratives, and excluded candidates.
- Existing acceptance artifacts still generate.

## Run Record

- `.ecc/runs/20260514-review-queue-artifact/`
