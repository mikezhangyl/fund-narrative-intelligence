# Candidate Narratives Execution Plan

## Purpose

Preserve a review-ready candidate narrative structure for excluded fallback candidates without promoting those candidates into the active scoring registry.

## Scope

- Populate `candidate_narratives` in the local narrative registry fixture.
- Validate the candidate narrative shape at provider boundaries.
- Emit in-scope candidate narratives in raw/scoring JSON.
- Render candidate narratives in Markdown/HTML reports and real-smoke summaries.
- Print candidate narrative counts in real-smoke CLI output.

## Non-Goals

- Promoting candidate narratives into active scoring.
- Adding stock-to-candidate scoring or aggregation.
- Replacing human review with automatic narrative discovery.

## Acceptance

- Tests cover provider validation, pipeline output, report rendering, real-smoke summary, and CLI output.
- Full quality gates pass.
- Real smoke shows candidate narrative counts while keeping excluded candidates out of scoring.

## Run Record

- `.ecc/runs/20260514-candidate-narratives/`
