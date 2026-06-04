# Product Documents

This directory contains product and architecture source documents for Fund Narrative Intelligence.

## Canonical Sources

- [Fund Narrative Intelligence System](./fund-narrative-intelligence-system.html)
- [V1 Implementation Spec](./v1-implementation-spec.md)
- [Narrative Mapping Methodology v0](./narrative-mapping-methodology-v0.md)
- [Narrative Service Boundary](./narrative-service-boundary.md)
- [Market Data Gateway Boundary](./market-data-gateway-boundary.md)
- [Narrative Service Implementation Request](./narrative-service-implementation-request-2026-05-28.md)
- [Narrative Store Migration Checklist](./narrative-store-migration-checklist.md)
- [Stock Narrative Service Bootstrap Prompt](./stock-narrative-service-bootstrap-prompt.md)
- [Stock Narrative Service Runbook](./stock-narrative-service-runbook.md)

## Current Product Definition

The system analyzes a fund through its holdings to identify market narratives, evaluate narrative sustainability, and produce an evidence-backed report. V1 is report-first, monolith-first, and mock-provider capable.

The first implementation loop is:

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

The system must not present output as investment advice or produce buy/sell signals.

Current narrative registry and stock-to-narrative mapping stores are local seed
knowledge, not trusted production knowledge. They are explicitly marked
`trust_status=untrusted_experimental` until a source-and-logic audit proves the
methodology and source chain. The runnable audit entry point is:

```bash
python scripts/run_narrative_mapping_trust_audit.py
```

The first candidate evidence-pack entry point is:

```bash
python scripts/run_mapping_evidence_pack_report.py --symbols 600519,000063,300308
```

Evidence packs are review inputs only. They must remain `candidate_untrusted`
until a human review and methodology audit promotes them.

The candidate narrative intake entry point is:

```bash
python scripts/run_candidate_narrative_intake.py
```

Intake accepts event-style records from future `news`, `announcement`,
`social`, and `manual` sources. It only emits candidate narratives, candidate
stock mappings, and review-queue items; it must not mutate the reviewed or
trusted stores automatically.

Structured news briefs can be converted into the same intake staging layer with:

```bash
python scripts/run_news_candidate_intake.py
```

This path consumes gateway/Tushare news briefs through a provider-neutral
contract, keeps direct crawling disabled, and records source trace rows for
candidate creation or reinforcement. The MIK-55 acceptance note is
`docs/product/structured-news-candidate-intake-2026-05-29.md`.

Structured announcement events can become review-only mapping evidence with:

```bash
python scripts/run_announcement_mapping_intake.py
```

This path links announcement evidence to candidate stock-to-narrative mappings,
keeps missing source URL/date as visible quality gaps, and never writes trusted
mapping state. The MIK-56 acceptance note is
`docs/product/announcement-mapping-intake-2026-05-29.md`.

Fund report packs now have a stable artifact manifest contract at
`config/fund_report_artifact_contract.json`. The MIK-65 acceptance note is
`docs/product/fund-report-artifact-contract-2026-05-29.md`.

Fund narrative exposure changes can be monitored with:

```bash
python scripts/run_fund_narrative_change_monitor.py
```

The MIK-57 acceptance note is
`docs/product/fund-narrative-change-monitor-2026-05-29.md`.

A static reviewable fund report pack can be built with:

```bash
python scripts/run_reviewable_fund_report_pack.py --artifact-root <pipeline-output-dir>
```

The MIK-58 acceptance note is
`docs/product/reviewable-fund-report-pack-2026-05-29.md`.

Governance audit exports use the schema at
`config/governance_audit_schema.json`. The MIK-66 acceptance note is
`docs/product/governance-audit-schema-2026-05-29.md`.

Narrative governance health can be exported with:

```bash
python scripts/run_narrative_governance_audit_export.py
```

The MIK-59 acceptance note is
`docs/product/narrative-governance-audit-export-2026-05-29.md`.

Narrative Service durable storage migration is documented in
`docs/product/narrative-service-storage-migration-path-2026-05-29.md`.

Narrative Radar ownership, deterministic score schema, and source-signal
time-series boundaries are documented in
`docs/product/narrative-radar-service-boundary-and-model-2026-05-29.html`.
The auxiliary Markdown note is
`docs/product/narrative-radar-service-boundary-and-model-2026-05-29.md`.

Narrative Radar deterministic heat/trend scoring and the market confirmation
adapter boundary are documented in
`docs/product/narrative-radar-scoring-and-confirmation-2026-05-29.html`.
The auxiliary Markdown note is
`docs/product/narrative-radar-scoring-and-confirmation-2026-05-29.md`.

Narrative Radar structured source mining into review-only candidate narratives
is documented in
`docs/product/narrative-radar-structured-source-mining-2026-05-29.html`.
The auxiliary Markdown note is
`docs/product/narrative-radar-structured-source-mining-2026-05-29.md`.

Narrative Radar bubble API and library-agnostic visualization contract are
documented in
`docs/product/narrative-radar-bubble-api-contract-2026-05-29.html`.
The auxiliary Markdown note is
`docs/product/narrative-radar-bubble-api-contract-2026-05-29.md`.

Narrative Radar evidence drill-down and review/trust state integration are
documented in
`docs/product/narrative-radar-evidence-review-detail-2026-05-29.html`.
The auxiliary Markdown note is
`docs/product/narrative-radar-evidence-review-detail-2026-05-29.md`.

Narrative Radar service preview payload and optional non-authoritative
explanation contract are documented in
`docs/product/narrative-radar-preview-and-explanation-contract-2026-05-29.html`.
The auxiliary Markdown note is
`docs/product/narrative-radar-preview-and-explanation-contract-2026-05-29.md`.

Round 4 live provider credential smoke and credential-safe diagnostics are
documented in
`docs/product/round4-live-provider-credential-smoke-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round4-live-provider-credential-smoke-2026-05-30.md`.

Round 4 Narrative Radar UI contract and service-owned operator surface are
documented in
`docs/product/round4-narrative-radar-ui-surface-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round4-narrative-radar-ui-surface-2026-05-30.md`.

Round 4 review workflow state machine, evidence review surface, and trust
promotion guardrails are documented in
`docs/product/round4-review-workflow-state-machine-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round4-review-workflow-state-machine-2026-05-30.md`.

Round 4 operational scheduling, job definitions, and run ledger are documented
in `docs/product/round4-operational-scheduling-run-ledger-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round4-operational-scheduling-run-ledger-2026-05-30.md`.

Round 4 durable storage migration readiness and lifecycle schema are documented
in `docs/product/round4-durable-storage-migration-readiness-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round4-durable-storage-migration-readiness-2026-05-30.md`.

Round 4 final productized narrative operations acceptance is documented in
`docs/product/round4-productized-narrative-operations-acceptance-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round4-productized-narrative-operations-acceptance-2026-05-30.md`.

Round 5 Evidence Intelligence and Narrative Quality adds Narrative Service-owned
quality scorecards, source lineage/reliability metadata, extraction quality
review, stale/contradiction detection, quality audit API, Chinese HTML quality
workspace, and deterministic JSON/HTML export:

```bash
uv run python scripts/run_narrative_quality_audit.py
```

The service endpoints are `/api/v1/narratives/quality/contract`,
`/api/v1/narratives/quality/scorecards`,
`/api/v1/narratives/quality/extractions`,
`/api/v1/narratives/quality/audit`, and `/narratives/quality`.
Quality metadata is owned by Narrative Service; FNI may consume it later but
must not recompute service quality scores.
Round 5 acceptance is documented in
`docs/product/round5-evidence-intelligence-quality-acceptance-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round5-evidence-intelligence-quality-acceptance-2026-05-30.md`.

Round 6 Portfolio and Fund Narrative Workspace adds watchlists/saved fund sets,
portfolio narrative exposure snapshots, snapshot comparison, observational
alerts, and radar-to-fund impact drill-down without recommendation language:

```bash
uv run python scripts/run_portfolio_narrative_workspace.py
```

The canonical readable output is Chinese HTML at
`portfolio_narrative_workspace.html`; JSON remains the machine-readable
contract. Round 6 acceptance is documented in
`docs/product/round6-portfolio-fund-narrative-workspace-acceptance-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round6-portfolio-fund-narrative-workspace-acceptance-2026-05-30.md`.

Round 7 Production Scale and Assisted Intelligence adds production readiness
health/runbook surfaces, data freshness/SLA metadata, citation-backed
AI-assisted explanations that can be disabled, and feedback records that create
review inputs without mutating trusted state:

```bash
uv run python scripts/run_production_readiness_assistant.py
```

The canonical readable output is Chinese HTML at
`production_readiness_assistant.html`; JSON remains the machine-readable
contract. Round 7 acceptance is documented in
`docs/product/round7-production-scale-assisted-intelligence-acceptance-2026-05-30.html`.
The auxiliary Markdown note is
`docs/product/round7-production-scale-assisted-intelligence-acceptance-2026-05-30.md`.

Narrative intelligence remains a future independent service boundary. FNI may
keep local prototypes for report integration and contract discovery, but the
future service should own registry lifecycle, stock mapping lifecycle, evidence
packs, candidate intake, trust audits, review queues, and trusted promotion.
The first FNI consumer contract is recorded in
`config/narrative_service_contract.yaml`, with local fallback implemented by
`src/providers/narrative_service.py`. When `NARRATIVE_SERVICE_URL` is
configured, FNI can now use `NarrativeServiceProvider` in service-first mode
with explicit local fallback through `FallbackNarrativeDataProvider`. Fund
holding exposure, fund exposure comparison, and fund narrative exposure matrix
reports disclose the narrative data source in JSON/HTML.

The provider smoke entry point is:

```bash
python scripts/run_narrative_service_provider_smoke.py
```

Set `NARRATIVE_SERVICE_URL` or pass `--base-url` to verify service-first HTTP
consumption. If the service is unavailable, the smoke should show an explicit
local fallback warning rather than a silent success.

The in-repo Narrative Service can be started with:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8800
```

The full local acceptance entry point is:

```bash
uv run python scripts/validate_stock_narrative_service_acceptance.py
```

Migration preparation is tracked in
`docs/product/narrative-store-migration-checklist.md`. Until the independent
service passes conformance, provider smoke, and at least one service-backed FNI
report, FNI local narrative files remain fallback/test fixtures rather than
authoritative service-owned truth.

The first engineering acceptance command is:

```bash
python scripts/validate_v1_acceptance.py
```

It must generate fund `000001`, validate generated artifact contracts, build and
validate a workspace snapshot, confirm mock data is visibly disclosed, and
produce raw JSON, scoring JSON, review queue, source table, manifest, Markdown
report, HTML report, signal trace, and workspace snapshot artifacts.

V1 can also list available mock fixtures:

```bash
python -m src.main --list-fixtures
```

And run all local mock scenarios:

```bash
python -m src.main --run-all-fixtures
```

Future web loading is prepared through:

```bash
python -m src.main --build-workspace-snapshot outputs/
python -m src.main --validate-workspace-snapshot outputs/fund_000001_workspace_snapshot.json
python -m src.main --validate-signal-trace outputs/fund_000001_signal_trace.json
```

The workspace snapshot includes top-level `data_source_notice`, `data_layers`,
`signal_trace`, and `approval_workflow` fields so a future web UI can display
mock/partial source warnings, provider payload availability/counts, score
provenance, and review-action state without rebuilding them from lower-level
artifacts.

The strict reviewed-mapping enriched acceptance path now uses explicit
Eastmoney valuation and financial metrics, and requires both valuation snapshots
and financial metrics to be visible in reports:

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```

The market-data capability inventory entry point is:

```bash
python scripts/report_data_capabilities.py --format html --output outputs/data_capabilities/latest.html
```

The same command supports `--format json` for machine-readable inventory and
`--format markdown` for auxiliary text output. The HTML output is the canonical
reader-facing surface for this inventory report.

Round 8 product shell starts with a concrete route registry and artifact index,
then renders a local product home and artifact browser:

```bash
uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current
```

The generated files are `route_registry.json/html`, `artifact_index.json/html`,
`product_shell.json`, `index.html`, and `artifact_browser.html`. The shell only
links existing APIs and generated artifacts; it does not recompute radar,
quality, portfolio exposure, or provider data. Acceptance for `MIK-165`,
`MIK-166`, `MIK-161`, and `MIK-162` is documented in
`docs/product/round8-product-shell-artifact-browser-acceptance-2026-05-31.html`.
The auxiliary Markdown note is
`docs/product/round8-product-shell-artifact-browser-acceptance-2026-05-31.md`.

The Round 4 to Round 13 PM/Architect stage review is documented in
`docs/product/pm-architect-stage-review-round4-round13-2026-06-02.html`.
It accepts the current local `main` as a stage checkpoint, recommends closing
completed Linear issues, keeps partial shell/release items open, and reaffirms
that real external source-event collection belongs in `stock-data-gateway`.
The auxiliary Markdown note is
`docs/product/pm-architect-stage-review-round4-round13-2026-06-02.md`.

The current-stage PM/Architect review for the product shell, real narrative
data entry, source quality, gateway boundary, and next-stage readiness is
documented in
`docs/product/pm-architect-current-stage-review-2026-06-03.html`.
The auxiliary Markdown note is
`docs/product/pm-architect-current-stage-review-2026-06-03.md`.

Narrative source expansion is now open-source-first for the current phase:
free public sources, official disclosure sources, and low-risk crawler pilots
take priority over paid terminals/news providers. The canonical strategy is
documented in
`docs/product/open-source-first-narrative-data-strategy-2026-06-04.html`.
The auxiliary Markdown note is
`docs/product/open-source-first-narrative-data-strategy-2026-06-04.md`.
