---
name: system-card-discovery
description: Use to build or update docs/testing/system-card.md from black-box observations, screenshots, UI navigation, roles, forms, flows, and browser network evidence.
---

# System Card Discovery

Use when new system behavior is observed.

## Rules

- Record observed facts with evidence.
- Mark uncertain conclusions as `inferred` or `unknown`.
- Do not convert guesses into verified facts.
- Prefer incremental updates over rewriting the whole card.

## Update Targets

- `docs/testing/system-card.md`
- current `.ecc/test-runs/<run-id>/observations/system-map.md`
- current `.ecc/test-runs/<run-id>/observations/flows.md`
- current `.ecc/test-runs/<run-id>/observations/api-observations.json`

## Status Labels

- `verified`: tested directly and repeatable
- `observed`: seen during testing but not exhaustively checked
- `inferred`: likely based on behavior or network evidence
- `unknown`: not known yet
- `stale`: previously observed but may no longer be true

