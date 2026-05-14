# Candidate Review Queue Execution Plan

## Purpose

Expose candidate narrative review work as a structured queue that can later be rendered by a web approval workspace.

## Scope

- Add review queue items for in-scope candidate narratives.
- Attach related exclusions and candidate metadata to each queue item.
- Include allowed actions and an approval action template.
- Emit queue data in JSON outputs and real-smoke summaries.
- Print queue item counts in real-smoke CLI output.

## Non-Goals

- Building web UI.
- Persisting review actions.
- Promoting candidates automatically.

## Acceptance

- Review queue is deterministic and workspace-ready.
- Empty candidate lists produce an empty queue.
- Existing scoring and report stages remain unchanged.

## Run Record

- `.ecc/runs/20260514-candidate-review-queue/`
