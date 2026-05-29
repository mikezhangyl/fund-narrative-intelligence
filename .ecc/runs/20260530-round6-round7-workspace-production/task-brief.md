# Task Brief

## Objective

Complete Round 6 and Round 7 requirements for Fund Narrative Intelligence.

## Linear Scope

- Round 6 / M12: `MIK-131`, `MIK-132`, `MIK-143` through `MIK-150`.
- Round 7 / M13: `MIK-133`, `MIK-134`, `MIK-151` through `MIK-158`.

## Implementation Boundaries

- FNI owns workspace aggregation, comparisons, alerts, production readiness
  exports, and reader-facing artifacts.
- Gateway remains the owner of holdings and market-data access.
- Narrative Service remains the owner of narrative radar, quality, evidence,
  trust state, and deterministic quality scoring.
- Alerts are observational only.
- AI assistance is explanatory only and cannot score, promote, or set trust
  state.

## Verification Gate

- Targeted TDD tests for Round 6 and Round 7.
- Ruff, compileall, full pytest.
- JSON/Chinese HTML CLI exports for both rounds.
