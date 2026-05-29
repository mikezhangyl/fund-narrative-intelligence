# Task Brief: Round 5 Evidence Intelligence & Narrative Quality

## Objective

Complete Linear M11 / Round 5 requirements for Fund Narrative Intelligence with TDD, checkpoint commits, verification evidence, and Linear closure.

## Linear Issues

- MIK-129 / MIK-130 parent requirement packs.
- MIK-135: Evidence quality scorecard.
- MIK-136: Structured event extraction quality review.
- MIK-137: Contradiction and stale narrative detection.
- MIK-138: Narrative quality audit workspace.
- MIK-139: Evidence quality schema and scoring contract.
- MIK-140: Source lineage and reliability model.
- MIK-141: Contradiction and staleness model.
- MIK-142: Narrative quality audit API and export contract.

## Constraints

- Narrative Service owns quality computation and audit outputs.
- Gateway/provider metadata can be preserved but no provider calls are made by quality scoring.
- No secret/token fields may be persisted in lineage.
- AI summaries cannot override deterministic quality scores.
- No automatic trusted promotion.

## Verification Policy

Use RED/GREEN TDD by slice. Record commands and generated artifacts in this run directory before final close-out.
