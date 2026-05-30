# Round 9-12 Product + Architecture Roadmap - 2026-05-30

## Roadmap Summary

Round 8 moves the product toward an integrated local shell. Round 9-12 should create enough planning buffer for the next phase:

1. Round 9 / M15: durable workspace persistence and personalization.
2. Round 10 / M16: narrative research workbench.
3. Round 11 / M17: historical replay and evaluation lab.
4. Round 12 / M18: collaboration governance and release readiness.

This roadmap intentionally designs ahead. The details can be revised later, but developer work should not stall for lack of PM/Architect requirements.

## Round 9 - Durable Workspace Persistence & Personalization

Milestone: `M15 - Durable Workspace Persistence & Personalization`

Goal: make the product shell stateful. Users should keep saved views, filters, preferences, and workspace state across sessions without storing secrets or mutating authoritative market/narrative records.

PM issues:

- MIK-169: `[PM-R9] Product requirement pack for durable workspace persistence and personalization`
- MIK-177: `[P0][PM-R9] Persistent workspace store and saved views`
- MIK-178: `[P1][PM-R9] User preferences and workflow defaults`
- MIK-179: `[P1][PM-R9] Workspace import and export package`

Architect issues:

- MIK-170: `[ARCH-R9] Architecture requirement pack for durable workspace persistence and personalization`
- MIK-180: `[ARCH-P0][R9] Workspace persistence schema and repository contract`
- MIK-181: `[ARCH-P1][R9] Preference redaction and validation contract`
- MIK-182: `[ARCH-P1][R9] Workspace import/export manifest contract`

Recommended developer order:

1. MIK-180 + MIK-177
2. MIK-181 + MIK-178
3. MIK-182 + MIK-179

Acceptance gate: saved workspace state, views, and preferences survive restart; export/import works; secrets are excluded or rejected.

## Round 10 - Narrative Research Workbench

Milestone: `M16 - Narrative Research Workbench`

Goal: give analysts a research surface for narrative timelines, source-event search, comparison, evidence graph exploration, and cited research exports.

PM issues:

- MIK-171: `[PM-R10] Product requirement pack for narrative research workbench`
- MIK-183: `[P0][PM-R10] Narrative timeline and source-event search`
- MIK-184: `[P1][PM-R10] Narrative comparison and evidence graph`
- MIK-185: `[P1][PM-R10] Analyst notes and research export pack`

Architect issues:

- MIK-172: `[ARCH-R10] Architecture requirement pack for narrative research workbench`
- MIK-186: `[ARCH-P0][R10] Timeline and search API contract`
- MIK-187: `[ARCH-P1][R10] Evidence graph and comparison model`
- MIK-188: `[ARCH-P1][R10] Analyst note and research export contract`

Recommended developer order:

1. MIK-186 + MIK-183
2. MIK-187 + MIK-184
3. MIK-188 + MIK-185

Acceptance gate: analysts can search evidence/source events, inspect narrative timelines, compare narratives, and export cited research notes without creating trusted records automatically.

## Round 11 - Historical Replay & Evaluation Lab

Milestone: `M17 - Historical Replay & Evaluation Lab`

Goal: evaluate system quality over time. This is not a trading backtest. It measures replay stability, source coverage, formula drift, quality drift, and alert noise/usefulness.

PM issues:

- MIK-173: `[PM-R11] Product requirement pack for historical replay and evaluation lab`
- MIK-189: `[P0][PM-R11] Historical replay runner`
- MIK-190: `[P1][PM-R11] Radar and quality stability evaluation`
- MIK-191: `[P1][PM-R11] Alert usefulness and noise review`

Architect issues:

- MIK-174: `[ARCH-R11] Architecture requirement pack for historical replay and evaluation lab`
- MIK-192: `[ARCH-P0][R11] Replay input and run schema`
- MIK-193: `[ARCH-P1][R11] Evaluation metric schema without trading claims`
- MIK-194: `[ARCH-P1][R11] Replay job storage and artifact contract`

Recommended developer order:

1. MIK-192 + MIK-189
2. MIK-193 + MIK-190
3. MIK-194 + MIK-191

Acceptance gate: replay runs are deterministic, bounded, artifact-backed, and clearly exclude return prediction, alpha claims, buy/sell success metrics, and portfolio optimization.

## Round 12 - Collaboration Governance & Release Readiness

Milestone: `M18 - Collaboration Governance & Release Readiness`

Goal: prepare the system for controlled handoff beyond one local user by adding collaboration bundles, backup/restore archives, release notes, and operator onboarding.

PM issues:

- MIK-175: `[PM-R12] Product requirement pack for collaboration governance and release readiness`
- MIK-195: `[P0][PM-R12] Collaborative review handoff workflow`
- MIK-196: `[P1][PM-R12] Backup restore and portable release archive`
- MIK-197: `[P1][PM-R12] Operator onboarding and release notes`

Architect issues:

- MIK-176: `[ARCH-R12] Architecture requirement pack for collaboration governance and release readiness`
- MIK-198: `[ARCH-P0][R12] Collaboration role and handoff model`
- MIK-199: `[ARCH-P1][R12] Backup restore archive schema`
- MIK-200: `[ARCH-P1][R12] Release governance and operator handoff contract`

Recommended developer order:

1. MIK-198 + MIK-195
2. MIK-199 + MIK-196
3. MIK-200 + MIK-197

Acceptance gate: a reviewer/operator can export a review handoff, create a restorable release/archive bundle, and follow onboarding/release notes without relying on chat history.

## Cross-Round Guardrails

- Gateway owns external data/provider access.
- Narrative Service owns narrative lifecycle, evidence quality, radar, trust, and source-event semantics.
- FNI owns workspace aggregation, shell, artifact browsing, reports, and monitoring outputs.
- Product shell and research surfaces must not recompute narrative scores client-side.
- User notes/preferences are local artifacts, not trusted market data.
- Replay evaluation is for system quality, not trading performance.
- AI assistance remains citation-backed, optional, and non-authoritative.
- Secrets must be rejected or redacted in all persistence/export surfaces.

## Next Developer Slice

After Round 8, start Round 9 with:

- MIK-180: Workspace persistence schema and repository contract
- MIK-177: Persistent workspace store and saved views

This makes the product shell stateful before adding deeper research and replay workflows.
