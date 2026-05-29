# Round 5-7 Product + Architecture Roadmap - 2026-05-30

## Roadmap Summary

Round 4 completed the productized operations layer. The next three rounds push the product forward in this order:

1. Round 5 / M11: improve evidence intelligence and narrative quality.
2. Round 6 / M12: build portfolio and fund narrative workspace workflows.
3. Round 7 / M13: harden production operations and add AI-assisted explanations with citations.

The sequence is intentional. Fund/portfolio workflows should not expand until narrative quality is visible and auditable. AI assistance should not arrive before deterministic evidence, freshness, and governance contracts are stable.

## Round 5 - Evidence Intelligence & Narrative Quality

Milestone: `M11 - Evidence Intelligence & Narrative Quality`

Goal: strengthen trustworthiness before expanding user-facing decision workflows. The product should show not only which narratives are hot, but also why evidence is credible, stale, weak, contradictory, or provider-degraded.

### PM Issues

- MIK-129: `[PM-R5] Product requirement pack for evidence intelligence and narrative quality`
- MIK-135: `[P0][PM-R5] Evidence quality scorecard`
- MIK-136: `[P0][PM-R5] Structured event extraction quality review`
- MIK-137: `[P1][PM-R5] Contradiction and stale narrative detection`
- MIK-138: `[P1][PM-R5] Narrative quality audit workspace`

### Architect Issues

- MIK-130: `[ARCH-R5] Architecture requirement pack for evidence intelligence and narrative quality`
- MIK-139: `[ARCH-P0][R5] Evidence quality schema and scoring contract`
- MIK-140: `[ARCH-P0][R5] Source lineage and reliability model`
- MIK-141: `[ARCH-P1][R5] Contradiction and staleness model`
- MIK-142: `[ARCH-P1][R5] Narrative quality audit API and export contract`

### Developer Order

1. MIK-139 + MIK-140
2. MIK-135 + MIK-136
3. MIK-141 + MIK-137
4. MIK-142 + MIK-138

### Acceptance Gate

Round 5 is accepted when narrative/evidence records expose replayable quality components, source lineage, extraction quality, stale/contradiction status, and an audit surface without using AI as the source of truth.

## Round 6 - Portfolio & Fund Narrative Workspace

Milestone: `M12 - Portfolio & Fund Narrative Workspace`

Goal: turn trusted narrative and quality data into user workflows for fund and portfolio monitoring. This is decision support, not financial advice or trading automation.

### PM Issues

- MIK-131: `[PM-R6] Product requirement pack for portfolio and fund narrative workspace`
- MIK-143: `[P0][PM-R6] Fund and portfolio narrative dashboard`
- MIK-144: `[P0][PM-R6] Watchlists and saved fund sets`
- MIK-145: `[P1][PM-R6] Narrative exposure change alerts`
- MIK-146: `[P1][PM-R6] Radar-to-fund impact drill-down`

### Architect Issues

- MIK-132: `[ARCH-R6] Architecture requirement pack for portfolio and fund narrative workspace`
- MIK-147: `[ARCH-P0][R6] Workspace entity and watchlist data model`
- MIK-148: `[ARCH-P0][R6] Narrative exposure snapshot and comparison API`
- MIK-149: `[ARCH-P1][R6] Alert rule engine contract`
- MIK-150: `[ARCH-P1][R6] Cross-service workspace boundary contract`

### Developer Order

1. MIK-147 + MIK-144
2. MIK-148 + MIK-143
3. MIK-150 + MIK-146
4. MIK-149 + MIK-145

### Acceptance Gate

Round 6 is accepted when a user can save funds/watchlists, view narrative exposure and quality, compare exposure snapshots, receive observational alerts, and drill from a heating radar narrative into affected funds/holdings without score recomputation or recommendation language.

## Round 7 - Production Scale & Assisted Intelligence

Milestone: `M13 - Production Scale & Assisted Intelligence`

Goal: prepare the platform for longer-running production use and add AI assistance only as citation-backed explanation. Deterministic scores, evidence, review state, and promotion ledgers remain authoritative.

### PM Issues

- MIK-133: `[PM-R7] Product requirement pack for production scale and assisted intelligence`
- MIK-151: `[P0][PM-R7] Production readiness dashboard and runbooks`
- MIK-152: `[P0][PM-R7] Data freshness and SLA monitoring`
- MIK-153: `[P1][PM-R7] AI-assisted narrative and evidence summaries with citations`
- MIK-154: `[P1][PM-R7] User feedback loop for narrative quality`

### Architect Issues

- MIK-134: `[ARCH-R7] Architecture requirement pack for production scale and assisted intelligence`
- MIK-155: `[ARCH-P0][R7] Observability and runbook contract`
- MIK-156: `[ARCH-P0][R7] Data freshness and SLA schema`
- MIK-157: `[ARCH-P1][R7] AI assistance safety and citation contract`
- MIK-158: `[ARCH-P1][R7] Feedback and access governance model`

### Developer Order

1. MIK-155 + MIK-151
2. MIK-156 + MIK-152
3. MIK-157 + MIK-153
4. MIK-158 + MIK-154

### Acceptance Gate

Round 7 is accepted when production health/freshness/runbook surfaces exist, stale or degraded data is visible, AI summaries cite source/evidence ids and can be disabled, and feedback records create audit/review inputs without directly mutating trusted state.

## Cross-Round Principles

- Gateway owns external provider access and provider degradation semantics.
- Narrative Service owns narrative lifecycle, evidence quality, radar, review, trust, and AI explanation contracts.
- FNI owns fund/portfolio aggregation, workspace/report consumption, and user-facing monitoring outputs.
- AI output is explanation only; it cannot score, predict, promote, or replace source evidence.
- Alerts are observational; they are not buy/sell signals.
- Every user-facing score or summary must expose source, freshness, confidence, and degradation details.

## Next Developer Slice

Start Round 5 with:

- MIK-139: Evidence quality schema and scoring contract
- MIK-140: Source lineage and reliability model

Then implement:

- MIK-135: Evidence quality scorecard
- MIK-136: Structured event extraction quality review

This gives Round 6 and Round 7 stronger inputs instead of building dashboards on weak narrative records.
