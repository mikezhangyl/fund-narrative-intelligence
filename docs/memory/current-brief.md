# Current Brief

Last updated: 2026-05-28

## Purpose

`fund-narrative-intelligence` is a Python report-first system for fund narrative sustainability analysis. A user enters a fund code; the pipeline reads holdings, maps holdings to market narratives, checks whether those narratives are supported by evidence, and emits structured JSON plus reader-facing HTML reports. The product is not a price predictor, trading signal generator, or investment advisor.

Project reporting rule: all formal reader-facing reports must include Chinese HTML output as the canonical readable artifact. JSON remains the machine-readable artifact. Markdown may exist only as auxiliary compatibility output and must not be the formal reading surface for new reports. Formal HTML reports should explain every metric and expose metric source/口径 details through hover/tooltips where practical.

## Data Source Platform Objective

The project is also evolving a trusted market-data capability layer. The goal is not merely to add APIs; it is to progressively answer which data each analysis workflow needs, how difficult each dataset is to obtain reliably, whether the local platform already has that capability, and what infrastructure is needed when it does not. Build this from simple to medium to complex sources with reliability, validation, cache/gateway readiness, and maintainability as first-class requirements.

Local market-data gateway coordination is document-driven. FNI owns the consumer contract in `config/market_data_gateway_contract.yaml`; the gateway project consumes FNI change requests from `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/`. Current gateway consumption has two surfaces: normalized REST via `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700`, and low-friction Tushare facade compatibility via `TUSHARE_API_URL=http://127.0.0.1:8700/tushare`.

Large Tushare daily-bar scans should go through the gateway async job surface, not the synchronous normalized daily route. `LocalGatewayMarketDataProvider` automatically routes daily-bar batches with `100` or more symbols to `POST /api/v1/market-data/jobs/daily-bars`, polls job status, and reads paginated rows. Tune with `MARKET_DATA_GATEWAY_ASYNC_DAILY_BARS_THRESHOLD`, `MARKET_DATA_GATEWAY_ASYNC_DAILY_BARS_MAX_WAIT_SECONDS`, and `MARKET_DATA_GATEWAY_ASYNC_DAILY_BARS_POLL_INTERVAL_SECONDS`.

Gateway normalized request timeout is configurable with `MARKET_DATA_GATEWAY_TIMEOUT_SECONDS`; the default is 10 seconds. Use a higher value for bounded live probes that are known to call slow public-web-backed gateway routes.

The next gateway blocker is breadth-scale cold-cache operation, not basic daily-bar access. FNI created `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/fni-breadth-scale-job-ops-change-request-2026-05-25.md` requesting job list/cancel/persistence/progress metadata/coverage reasons and a breadth-window cache-warming job.

After gateway job-ops landed, FNI integrated `breadth-window` into `execute_breadth_scan`; reports now include `data_fetch_mode`. FNI intentionally does not fallback from terminal cancelled/failed/interrupted breadth-window jobs to daily-bars, because that recreates the old heavy path. The gateway retry/resume fix for cancelled semantic breadth-window jobs was verified on 2026-05-25 with a 500-symbol, 20-trading-day scan: gateway job `breadth-window-ef97409a50b8feec` completed with 500 completed symbols, 0 failed symbols, 9940 rows, 285 cache-hit symbols, and 215 upstream-fetch symbols.

The market-data lane should now prioritize "Can Do" capability expansion over extreme backend robustness. Keep throughput, scheduling, cache-warming, and richer operational diagnostics as TODO/backlog items, but do not let them block the next functional datasets. The active execution plan is `docs/exec-plans/active/market-data-can-do-roadmap.md`.

Two source clues are now part of the market-data roadmap: `https://sckd.dapanyuntu.com/` is a market-breadth definition/reference target where breadth is close-above-MA20 percentage, not a scraping target; Tushare `news` is the preferred structured news source before direct news-site crawling, but it likely needs a permission and smoke-test check before integration.

Market-data source breakthroughs should now be gateway-owned. FNI should express new needs as consumer-contract updates and gateway change-request documents, then implement scanners/reports against the gateway API. Avoid adding new direct Tushare, AkShare, EastMoney, or news-site integrations inside FNI unless needed as a small compatibility shim. The Can-Do gateway pack was accepted on 2026-05-25 and should be read from `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-can-do-market-data-capability-pack-change-request-2026-05-25.md`. Accepted live surfaces: provider-neutral sector concepts, ETF spot, provider-neutral limit-up/down, and Tushare news briefs. FNI smoke outputs live under `outputs/can_do_probes/2026-05-25-*`; summary report: `outputs/data_capabilities/fni_can_do_market_data_acceptance_2026-05-25.md`.

FNI now has a Can-Do daily market structure report at `scripts/run_daily_market_structure_report.py`. It combines breadth-window market breadth, index/ETF benchmark daily bars, sector heat, ETF spot heat, limit-up/down temperature, gateway flow/event context, gateway CYQ cost-basis samples, and gateway Tushare news briefs into JSON/HTML outputs under `outputs/daily_market_structure/`. The report includes deterministic title-level news deduplication and explicit data-gap diagnostics for connected interfaces.

CYQ chip distribution is available through gateway `/api/v1/market-data/chips/cyq`; FNI conformance passed for this route on 2026-05-26. FNI now exposes it through `LocalGatewayMarketDataProvider.fetch_cyq_chips` and `ConsolidatedMarketDataSource.fetch_cyq_chips`, has a runnable probe at `scripts/run_cyq_chips_probe.py`, and the daily market structure report renders a small cost-basis context section with distribution bucket count and peak bucket. Northbound capital, main capital flow, ETF flow, and 龙虎榜 are available through provider-neutral gateway routes as of 2026-05-27. The flow/event gateway request is archived at `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-flow-and-event-data-capability-pack-change-request-2026-05-26.md`. FNI smoke outputs live under `outputs/flow_event_probes/2026-05-27-*`. A light repeated live check showed the four flow/event routes are Can-Do stable enough to continue functional expansion, but public-web-backed data should remain auxiliary until longer validation proves production reliability. Daily market structure report now consumes these routes directly and renders northbound direction, top money-flow samples, ETF-flow samples, dragon-tiger samples, and deterministic cross-links against structure rows.

The structure mapping gateway request is accepted and archived at `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-structure-mapping-data-capability-pack-change-request-2026-05-27.md`. Provider-neutral routes for sector constituents, ETF basic metadata, index constituents, margin summary/detail, and earnings/event calendar data are available as of 2026-05-27. FNI smoke outputs live under `outputs/structure_mapping_probes/2026-05-27-*`.

Current market-data caveat: provider-neutral sector concepts remain unstable. On 2026-05-27 the sector concepts route and legacy AkShare-specific sector concepts route returned HTTP 500, while sector constituents worked through EastMoney fallback. ETF spot passed when checked alone with a longer timeout but timed out during broad default conformance.

FNI now has a Can-Do structure mapping report at `scripts/run_structure_mapping_report.py`. It combines sector constituents, ETF basic metadata, index constituents, margin summary/detail, and earnings/event calendar data into JSON/HTML outputs under `outputs/structure_mapping_report/`. A live run on 2026-05-27 completed with 51 rows across the six components.

Daily market structure report now embeds a structure mapping section. The HTML renderer temporarily marks that newly added section in red via `class="new-update"` so the update is easy to review; remove that styling after acceptance. The section should show deterministic explanatory context, including theme/index, theme/margin, theme/event-calendar, and index/margin overlaps, not just task or endpoint status.

Stock -> sector/concept reverse membership is now gateway-implemented and FNI-consumed. FNI exposes it through `LocalGatewayMarketDataProvider.fetch_stock_sector_memberships`, `ConsolidatedMarketDataSource.fetch_stock_sector_memberships`, `scripts/run_stock_sector_memberships_probe.py`, and `scripts/run_holding_sector_exposure_report.py`. The archived gateway request is `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-stock-sector-membership-data-capability-pack-change-request-2026-05-27.md`. Current local smoke may return structured degraded payloads when EastMoney/AkShare public upstreams are unreachable, so keep the dataset status as `unstable` until repeated live rows are observed. FNI probes and reports accept `sector_universe_limit`; use `0` for seed-only Can-Do checks and raise it only when the upstream path is stable enough.

FNI runtime note: on 2026-05-27 the LaunchAgent-backed gateway at `http://127.0.0.1:8700` was restarted to the current gateway checkout, then gateway-side timeout hardening landed. The stock-sector membership route no longer returns 404 or hangs until FNI socket timeout. A bounded live run with `MARKET_DATA_GATEWAY_TIMEOUT_SECONDS=20` and `--sector-universe-limit 0` returned through FNI as `missing` with no rows and a provider-degraded event: `REQUEST_TIMEOUT: Stock sector membership reverse index materialization timed out.` Outputs: `outputs/stock_sector_memberships_probe/2026-05-27-gateway-timeout-fix/` and `outputs/holding_sector_exposure/2026-05-27-gateway-timeout-fix/`.

Latest accepted gateway breakthrough: fund profile and fund holdings. Gateway archived the request at `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-fund-profile-and-holdings-data-capability-pack-change-request-2026-05-27.md`. FNI now marks `gateway_fund_profile` and `gateway_fund_holdings` as available, with `fund_profile`/`fund_holdings` as `gateway_ready`. `provider_mode=gateway` routes fund reports through `LocalGatewayFundHoldingProvider`; live conformance passed for `161725`, and the gateway-backed report returned 10 fresh holdings with no FNI degradation events. Keep using holdings rows, not profile metadata, as the report disclosure date/source. Lightweight probe: `scripts/run_fund_profile_holdings_probe.py`. Outputs: `outputs/gateway_contract/2026-05-27-fund-profile-holdings.json`, `outputs/gateway_fund_provider_smoke/2026-05-27-live-fund-holdings-v2/`, and `outputs/fund_profile_holdings_probe/2026-05-27-live-gateway/`.

FNI now has a Can-Do fund holding exposure report at `scripts/run_fund_holding_exposure_report.py`. It starts from a fund code, pulls gateway profile/holdings, aggregates holding-row industry exposure, links holdings to local reviewed narrative mappings, and attempts stock-sector membership for sector/concept exposure. Live 161725 output on 2026-05-28: `outputs/fund_holding_exposure/2026-05-28-live-gateway/`; status is `partial` because stock-sector membership still degraded/missing, but holdings, industry exposure, and `N_BAIJIU_CONSUMPTION` narrative exposure are usable.

FNI now also has a Can-Do multi-fund exposure comparison report at `scripts/run_fund_exposure_comparison_report.py`. It compares gateway-backed fund holdings, concentration, holding overlap, common narrative exposure, and differentiating narrative exposure across multiple funds. Live output on 2026-05-28 for `161725,515880,512760`: `outputs/fund_exposure_comparison/2026-05-28-live-gateway/`; status is `partial` because stock-sector membership timed out through structured gateway degradation, but holdings/concentration/narrative differences are usable.

FNI now has a Can-Do fund narrative exposure matrix report at `scripts/run_fund_narrative_exposure_matrix_report.py`. It renders a fund-by-narrative matrix plus high-homogeneity fund pairs, narrative coverage, differentiating narratives, and data gaps. Live output on 2026-05-28 for `161725,515880,512760`: `outputs/fund_narrative_exposure_matrix/2026-05-28-live-gateway/`; status is `partial`, with 5 narrative columns, 0 high-homogeneity pairs, and structured stock-sector membership degradation.

Narrative governance note: the current reviewed narrative registry and reviewed stock-to-narrative mapping store are explicitly marked `trust_status=untrusted_experimental`. In this project, `reviewed` means the local seed files passed syntax/audit metadata checks and limited approval steps; it does not mean the source chain, mapping logic, or validation criteria are rigorous enough to treat the narratives as trusted production knowledge. Reports should disclose this trust status and use narrative exposure only for observation/audit until a dedicated source-and-logic audit promotes the stores.

FNI now has a first narrative mapping methodology document at `docs/product/narrative-mapping-methodology-v0.md` and a trust audit script at `scripts/run_narrative_mapping_trust_audit.py`. The audit intentionally blocks the current reviewed stores from `trusted_validated`: live output on 2026-05-28 showed 56/56 mappings missing formal source evidence and rationale, 15/15 narratives missing complete evidence chains, and 12/15 narratives missing exclusion criteria. Output: `outputs/narrative_mapping_trust_audit/2026-05-28-reviewed-store/`.

FNI now has a first Mapping Evidence Pack v0 seed file at `data/registry/mapping_evidence_packs.v0.json` and report CLI at `scripts/run_mapping_evidence_pack_report.py`. The first three candidate packs are `600519 -> N_BAIJIU_CONSUMPTION`, `000063 -> N_COMMUNICATION_EQUIPMENT`, and `300308 -> N_OPTICAL_MODULE_CHAIN`; all remain `candidate_untrusted` and are review inputs only. Live output: `outputs/mapping_evidence_pack/2026-05-28-seed3/`.

FNI now has Candidate Narrative Intake v0 at `scripts/run_candidate_narrative_intake.py`, backed by sample events in `data/fixtures/candidate_narrative_events.v1.json`. Intake supports future `news`, `announcement`, `social`, and `manual` event sources, emits only `candidate_untrusted` candidate narratives / stock mappings / review queue items, and never mutates reviewed or trusted stores automatically. Sample output on 2026-05-28 created one new candidate narrative (`机器人执行器`), one existing narrative evidence reinforcement (`N_BAIJIU_CONSUMPTION`), and four candidate mapping review items: `outputs/candidate_narrative_intake/2026-05-28-sample-events/`.

Narrative intelligence remains a future independent service boundary, documented at `docs/product/narrative-service-boundary.md` with migration plan `docs/exec-plans/active/narrative-service-migration-roadmap.md`. FNI owns report consumption, local prototypes, diagnostics, and contract validation; the future narrative service should own registry and mapping lifecycle, evidence packs, candidate intake, trust audits, review queues, and trusted promotion. New FNI narrative work should be shaped as a service contract or local fallback provider, not permanent FNI-owned narrative storage.

## Default Context Budget

Use this file as the default memory entry point. Do not read `docs/memory/project-context.md`, `docs/memory/architecture-decisions.md`, every execution plan, or `.ecc/runs/**` by default. Load those heavier files only when the task asks for history, architecture rationale, a named plan, or a specific run artifact.

Default startup context:

- `.ecc/framework-state.json`
- `docs/memory/operating-rules.md`
- `docs/memory/current-brief.md`
- `docs/memory/architecture-decisions.index.md`
- `docs/exec-plans/active/index.md`
- newest relevant `.ecc/runs/<task-run-id>/run-state.json` only when continuing a known run

In `.ecc/framework-state.json`, `default_skills` and `library_skills` are project-local harness metadata. `default_skills` are startup skills; `library_skills` are installed and available but should be loaded only when the task triggers them.

For a compact machine-generated view, run:

```bash
python scripts/context_brief.py --max-words 900
```

## Current Shape

- Runtime: Python CLI, standard-library-first.
- Test runner: pytest.
- Quality commands: `python -m ruff check .`, `python -m coverage run -m pytest -q`, `python -m coverage report`, `python -m compileall -q src tests scripts`.
- Mock baseline: deterministic fixtures keep V1 runnable without credentials.
- Real providers: Eastmoney holdings/market/valuation/financial paths, CNINFO announcements, Google News RSS, Sina Finance headlines, optional Tushare and AKShare routing.
- Future UI: web approval workspace remains deferred; current JSON artifacts should stay web-loadable.

## Stable Product Loop

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

Important generated artifacts include raw/scoring JSON, review queue, source table, signal trace, manifest, reader-facing report HTML, and workspace snapshot.

## Current Work Areas

- Hong Kong fund demo support, especially market-aware symbol resolution and explicit unsupported-provider handling.
- Provider routing across Eastmoney, AKShare, Tushare, and fallback behavior.
- Narrative intelligence service lane for source scouting, candidate generation, and human-gated registry/mapping changes.
- Evidence source diversification while keeping default evidence source quality disciplined.
- Harness token-budget optimization: summary-first memory, active-plan curation, and context loader usage.

## Read More Only When Needed

- Full project facts: `docs/memory/project-context.md`
- Full decision history: `docs/memory/architecture-decisions.md`
- Decision index: `docs/memory/architecture-decisions.index.md`
- Product spec: `docs/product/v1-implementation-spec.md`
- Active task queue: `docs/exec-plans/active/index.md`
- Historical run evidence: `.ecc/runs/<task-run-id>/`

## Operating Rules

- Parent execution is the default for small tasks.
- Execute directly when the next step is clear; ask only for unsafe/destructive actions, missing credentials/external access, or decisions that cannot be inferred safely.
- Use `ecc-task-subagent-workflow` only for multi-file, risky, long-running, autonomous, parallel, or PR-bound work.
- Formal reader-facing reports must include Chinese HTML as the canonical readable artifact; JSON is machine-readable, Markdown is auxiliary only.
- Formal report metrics should explain meaning and expose source / 口径 details through hover/tooltips where practical.
- Never scan all active plans or all run directories for routine work.
- Tell the user when a chat boundary is reached and provide a short handoff; the assistant cannot create or switch chats directly.
- Update this brief when a stable project fact changes enough that future sessions need it at startup.
