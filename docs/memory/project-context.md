# Project Context

## Project

- Name: fund-narrative-intelligence
- Status: V1 mock pipeline implemented
- Framework: merged ECC + Superpower + memory

## Product Goal

Build a Fund Narrative Intelligence System: users enter a fund code, the system reads or mocks the fund's top holdings, infers the market narratives the fund is exposed to, evaluates whether those narratives are still supported by evidence, and generates a report with supporting and risk evidence.

The product is a narrative sustainability analysis system, not a short-term price predictor, buy/sell signal generator, or automated investment advisor.

Canonical product source:

- `docs/product/fund-narrative-intelligence-system.html`
- `docs/product/v1-implementation-spec.md`

## Primary User

Experienced individual investors or researchers who want to understand what market narratives a fund is effectively betting on and whether those narratives remain supported.

## V1 Loop

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

## V1 Scope

- Input a fund code.
- Fetch or mock the fund's top ten holdings.
- Preserve the Fund -> Stock mapping.
- Map stocks to multi-level weighted narratives with confidence.
- Aggregate primary and secondary fund narrative exposure.
- Score narrative sustainability across five dimensions: earnings validation, capital reinforcement, valuation pressure, narrative momentum, and counter-evidence risk.
- Generate Markdown / HTML reports with evidence and an explicit non-investment-advice disclaimer.
- Support mock providers so V1 runs without real API credentials.
- Emit raw JSON, scoring JSON, Markdown report, and HTML report artifacts under `outputs/`.
- Emit a dedicated review queue JSON artifact for future web approval workspace loading.
- Emit a dedicated source table JSON artifact for future web source/provenance table rendering.
- Emit a dedicated signal trace JSON artifact for future web score-provenance rendering.
- Emit workspace snapshot `data_layers` summaries for future web data-tab loading.

## V1 Acceptance Command

`python scripts/validate_v1_acceptance.py`

The script generates fund `000001` into a temporary directory, runs
`--validate-artifact-contracts`, builds and validates a workspace snapshot, and
checks mock source URL disclosure, manifest web-readiness, review queue/source
table presence, workspace mock `data_source_notice`, workspace `data_layers`
mock source disclosure, and report data-source notices.

Expected artifacts:

- `outputs/fund_000001_raw.json`
- `outputs/fund_000001_scoring.json`
- `outputs/fund_000001_review_queue.json`
- `outputs/fund_000001_source_table.json`
- `outputs/fund_000001_signal_trace.json`
- `outputs/fund_000001_manifest.json`
- `outputs/fund_000001_report.md`
- `outputs/fund_000001_report.html`
- `outputs/fund_000001_workspace_snapshot.json` (built by the acceptance script)

## Technical Stack

- V1 engine: Python CLI.
- Runtime dependencies: standard library only for the first mock pipeline.
- Test runner: pytest.
- Development quality tools: pytest, ruff, and coverage are declared in `pyproject.toml` under the `dev` extra.
- Standard setup command: `python -m pip install -e ".[dev]"`.
- Standard quality commands: `python -m ruff check .`, `python -m coverage run -m pytest -q`, `python -m coverage report`, and `python -m compileall -q src tests scripts`.
- Standard V1 acceptance command: `python scripts/validate_v1_acceptance.py`.
- Strict live Eastmoney holdings acceptance command: `python scripts/validate_real_holdings_acceptance.py --output-dir outputs/real_161725`.
- Strict live Eastmoney + CNINFO announcement acceptance command: `python scripts/validate_announcement_acceptance.py --output-dir outputs/announcement_161725`.
- GitHub Actions CI runs the standard quality gates on pushes to `main` and pull requests.
- Data: local JSON fixtures and mock providers.
- Future UI: Node.js / Next.js can be added later as a separate workspace layer. Candidate narrative review and approval will eventually happen in a web UI, so V1 structured outputs should remain directly renderable and action-ready for a future review workspace.
- CLI fixture discovery: `python -m src.main --list-fixtures`.
- Batch fixture command: `python -m src.main --run-all-fixtures`.
- Live Eastmoney smoke command: `python -m src.main --run-real-smoke`.
- Live Eastmoney + CNINFO announcement smoke command: `python -m src.main --run-announcement-smoke`.
- Provider diagnostics command: `python -m src.main --fund-code 000001 --provider-diagnostics` prints provider foundation JSON without generating report artifacts.
- Optional CNINFO announcement evidence command: `python -m src.main --fund-code 000001 --include-cninfo-announcements --announcement-start-date 2026-05-01`.
- Optional market quote snapshot command: `python -m src.main --fund-code 161725 --provider-mode eastmoney --include-market-quotes`.
- Optional quote-derived valuation context command: `python -m src.main --fund-code 161725 --provider-mode eastmoney --include-market-quotes --include-valuation-snapshots`.
- Optional Eastmoney valuation metrics command: `python -m src.main --fund-code 161725 --provider-mode eastmoney --include-valuation-snapshots --valuation-source eastmoney`.
- Optional Eastmoney financial metrics command: `python -m src.main --fund-code 161725 --provider-mode eastmoney --include-financial-metrics`.
- Optional RSS-derived news evidence command: `python -m src.main --fund-code 000001 --include-news-evidence`.
- Strict live market quote acceptance command: `python scripts/validate_market_quotes_acceptance.py --output-dir outputs/market_quotes_161725`.
- Provider payloads are validated before orchestration proceeds.
- Real holdings adapter: `python -m src.main --fund-code 161725 --provider-mode eastmoney` tries Eastmoney/Tiantian Fund fund holdings and keeps local fixtures for all other V1 intelligence layers.
- Strict real-holdings acceptance validates fund `161725` with Eastmoney holdings and fixture-backed registry/mapping/evidence/signal layers. It fails on provider fallback instead of accepting mock degradation.
- Provider foundation metadata separates holdings, narrative registry, stock mappings, evidence, and signals so mixed real/mock runs are marked `partial` instead of `fresh`.
- Mock intelligence layer providers now expose separate interfaces for registry, stock mappings, evidence, signals, and reserved market/valuation/announcement/news sources.
- Optional `CNInfoAnnouncementProvider` exists as the first real intelligence-source adapter foundation; it is not wired into the default report pipeline.
- Optional announcement-to-evidence conversion and orchestration exist for CNINFO-style announcement metadata; default reports do not call CNINFO unless `--include-cninfo-announcements` is set.
- CNINFO announcement search for Shanghai and Shenzhen A-shares must send `stock` as `code,orgId`, for example `600519,gssh0600519` or `000001,gssz0000001`; using only the 6-digit code can return empty results.
- Markdown and HTML reports include a `Data Source Notice` whenever a run uses mock data, fallback/degradation, or mixed real/mock layers.
- Mock-backed holdings and fixture-backed intelligence layers use `mock://fixtures/...` source identifiers so raw/scoring JSON and future web source tables visibly mark non-real data at the source field.
- HTML reports render semantic sections/tables directly from structured scoring data.
- Mapping output includes coverage ratio, mapping method counts, and unmapped holdings.
- Unmapped holdings can receive low-confidence `registry_term_rule` mappings from narrative registry aliases/related terms matched against stock name and industry.
- Multi-match `registry_term_rule` mappings are retained but lowered from confidence `0.52` to `0.42`, marked `needs_review`, and emitted as `mapping_precision_flags`.
- Single fallback mappings supported only by broad holding industry terms are lowered from confidence `0.52` to `0.48`, marked `broad_industry_fallback`, and emitted with `curation_review`.
- Selected stock-to-narrative mappings also emit `mapping_rationales` in raw/scoring JSON and reports, including method, confidence, matched registry terms, and review flags so users can see why a holding was mapped to a narrative.
- `--stock-mapping-mode registry-rule` skips the static stock mapping fixture for a single `--fund-code` report run and derives all selected mappings from current holdings plus Narrative Registry terms. In that mode the `Stock Mappings` provider layer becomes `registry-rule-stock-mapping`, while the Narrative Registry layer remains Mock-backed and visibly disclosed. Fully mock-backed runs remain `mock`; runtime mapping does not upgrade mock inputs to `partial`.
- `python scripts/validate_registry_rule_enriched_acceptance.py --output-dir outputs/registry_rule_enriched_161725` is the strict live-provider acceptance command for the enriched path without static stock mapping fixtures. It requires `registry_term_rule` mappings, a runtime `Stock Mappings` layer, and visible disclosure of remaining Mock-backed layers.
- `--base-intelligence-mode provider-derived` skips base evidence and signal fixtures for a single enriched report run, requires CNINFO announcements, and uses generated announcement evidence plus derived provider signals as the only evidence/signal inputs. `python scripts/validate_provider_derived_enriched_acceptance.py --output-dir outputs/provider_derived_enriched_161725` is the strict live-provider acceptance command for this path.
- `--narrative-registry-mode reviewed` loads a file-backed Narrative Registry store for reviewed workflows, defaulting to `data/registry/narrative_registry.reviewed.json`, and replaces the `Narrative Registry` provider layer with non-mock `reviewed-registry-store`. `--narrative-registry-path` is allowed only with reviewed mode and only for single `--fund-code` report runs.
- `python scripts/validate_reviewed_registry_enriched_acceptance.py --output-dir outputs/reviewed_registry_enriched_161725` is the strict live-provider acceptance command for the first no-mock-core-intelligence enriched path: Eastmoney holdings, reviewed registry, registry-rule mappings, provider-derived evidence/signals, CNINFO announcements, and market quotes.
- `--stock-mapping-mode reviewed` loads explicit stock-to-narrative mappings from `data/registry/stock_narrative_mappings.reviewed.json` or `--stock-mappings-path`, uses mapping method `reviewed_mapping`, and replaces the `Stock Mappings` provider layer with non-mock `reviewed-mapping-store`.
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725` is the strict live-provider acceptance command for the enriched path with reviewed registry and reviewed mappings; it rejects `fixture_rule` and `registry_term_rule` selected mappings, includes Eastmoney valuation metrics and Eastmoney financial metrics, and builds/validates `fund_161725_workspace_snapshot.json` for future web loading.
- Reviewed registry and reviewed mapping providers require store-level `review_metadata`; active reviewed narratives require non-empty `reviewed_by` and `reviewed_at`; reviewed mapping rows require `review.status=approved`, `reviewed_by`, and `reviewed_at`.
- Reviewed provider foundation layers preserve store-level `review_metadata` so raw/scoring/review-queue/manifest artifacts can power future web source tables without reopening reviewed store files.
- Narrative reports include deterministic stage, risk, and confidence interpretation notes; these are explanatory and non-advisory.
- Real-fund smoke summaries isolate failures per fund, write summary artifacts, include concrete unmapped holding details, and return non-zero when any fund fails or falls below coverage threshold.
- Real-fund smoke summaries also include `multi_mapped_holdings` so 100% mapping coverage does not hide broad or cross-domain registry matches.
- Real-fund smoke summaries also aggregate `mapping_precision_flags` into JSON and Markdown so registry curation work items are visible without opening each fund report.
- Explicit mapping exclusions prevent known-bad fallback candidates from entering scoring; excluded candidates are emitted in raw/scoring JSON, reports, and real-smoke summaries.
- Review-only candidate narratives are emitted for related exclusions but do not enter active scoring until promoted by human review.
- Future candidate-narrative approval is expected to be a web workflow. V1 does not need web interaction yet, but candidate/exclusion objects should preserve stable IDs, review status, rationale, related stock/exclusion links, and nullable reviewer metadata for later UI actions.
- Candidate review actions support explicit `approve`, `reject`, and `defer` transitions. Only `approve` with promotion metadata appends an active narrative; report generation never promotes candidates automatically.
- Raw/scoring JSON includes `candidate_review_queue`, a read-ready queue for future web approval screens with available actions, related exclusions, and promotion action templates.
- Pipeline outputs include `fund_<code>_review_queue.json`, a dedicated future-workspace artifact containing the queue plus candidate/exclusion context.
- Pipeline outputs include `fund_<code>_source_table.json`, a dedicated future-workspace artifact containing provider-foundation source rows, mock flags, data quality, degradation events, and reviewed-store metadata when present.
- Pipeline outputs include `fund_<code>_signal_trace.json`, a dedicated future-workspace artifact containing per-narrative score traces from signal events to scoring dimensions, with source provider, source URL, source layer, and mock/provider-derived status.
- Pipeline outputs include `fund_<code>_manifest.json`, a web-ready discovery artifact with relative artifact paths, provider foundation, data quality, and degradation events.
- `python -m src.main --validate-artifact-manifest path/to/fund_000001_manifest.json` validates a manifest artifact without requiring `--fund-code`.
- `python -m src.main --validate-artifact-contracts path/to/outputs_or_manifest` validates known generated artifact contracts in one command before future web workspace loading, including manifest-referenced source-table and signal-trace artifacts plus generated workspace snapshots.
- `python -m src.main --validate-signal-trace path/to/fund_000001_signal_trace.json` validates a signal trace artifact without requiring `--fund-code`.
- `python -m src.main --build-workspace-snapshot path/to/outputs_or_manifest` writes `fund_<code>_workspace_snapshot.json`, a future-web loader artifact that bundles the manifest, provider foundation, source table, signal trace, review queue, narrative summaries, report paths, data-layer summaries, and approval workflow readiness metadata.
- `python -m src.main --validate-workspace-snapshot path/to/fund_000001_workspace_snapshot.json` validates that loader artifact without building UI.
- Workspace snapshots include a top-level `data_source_notice` object so future web screens can immediately display mock/partial/unavailable/degraded source warnings instead of inferring them from provider layers. They also include `data_layers.version = workspace-data-layers-v1` with layer availability, provider name, data quality, mock flag, source URL, artifact reference, and item count for web data tabs. They also include `approval_workflow.review_queue_summary`, `available_actions`, and item counts for future web approval routing. The V1 acceptance script explicitly validates this for the mock baseline so mock-backed web loader data cannot be mistaken for a real environment.
- `python -m src.main --validate-review-queue path/to/fund_000001_review_queue.json` validates a review queue artifact without requiring `--fund-code`.
- `python -m src.main --preview-review-action path/to/action.json` writes a review-action preview artifact without requiring `--fund-code` and without mutating `data/fixtures/narrative_registry.json`.
- Review-action preview artifacts include `registry_delta` so future web approval screens can show added active narratives and candidate state transitions without diffing the full registry.
- Review-action preview artifacts are validated before write; the reusable validator checks preview metadata, summary, registry delta, and result registry shape.
- `python -m src.main --validate-review-preview path/to/preview.json` validates a review preview artifact without requiring `--fund-code`.
- `python -m src.main --persist-review-action path/to/action.json --registry-output path/to/registry.next.json` writes an explicitly reviewed registry result without requiring `--fund-code`; in-place overwrite requires `--allow-registry-overwrite`, and overwriting an existing non-source output requires `--allow-registry-output-overwrite`.
- Review-action persistence writes a separate `candidate_review_action_<action_id>_persistence.json` audit artifact under `--output-dir` by default, or to `--persistence-result-output` when provided.
- Review-action persistence requires an audit output path or directory even for direct API callers; registry and audit writes are rollback-protected so audit write failure does not leave a new registry output behind.
- Review-action persistence result artifacts are validated before write, including overwrite policy flags and registry delta shape.
- `python -m src.main --validate-persistence-result path/to/persistence-result.json` validates a persistence audit artifact without requiring `--fund-code`.
- `python -m src.main --run-real-smoke` prints `precision_flags=<count>`, `excluded_candidates=<count>`, `candidate_narratives=<count>`, and `review_queue=<count>` per fund in stdout.
- Announcement-evidence smoke summaries check real CNINFO metadata count, converted evidence count, the non-mock `Announcements` layer, and visible mixed/mock data-source disclosure.
- Strict announcement acceptance validates the generated fund artifacts directly: Eastmoney holdings must be fresh, CNINFO announcements and converted evidence must be present, and remaining registry/mapping/base-evidence/signal layers must still disclose `mock://fixtures/...`.
- Optional CNINFO announcement runs now derive scoring signals from generated announcement evidence. Positive earnings/orders/capital announcements affect the matching score dimensions, negative risk announcements affect counter-evidence risk, and mixed financial/governance disclosures become low-weight momentum signals.
- Optional market quote runs now derive scoring signals from quote change percentages. Positive changes become `relative_strength_up`; negative changes become `relative_strength_down`, a capital-score risk signal.
- Optional valuation snapshot runs default to lightweight `quote-derived-valuation` context from market quotes. With `--valuation-source eastmoney`, runs fetch Eastmoney quote-detail valuation metrics into `valuation_snapshots` and add a non-mock `Valuation` provider layer named `eastmoney-valuation`. This is still not a full financial-statement or historical-percentile valuation feed.
- Optional Eastmoney valuation metric runs now derive `valuation-derived-signals` from provider valuation snapshots. Elevated metrics become `valuation_extreme`; discounted metrics become `valuation_reset`; quote-derived valuation context does not produce these scoring signals.
- Reports render an optional `Valuation Snapshots` section when `valuation_snapshots` is present, including stock, valuation basis, latest price, price change, PE TTM, PB, valuation pressure, provider, and source URL.
- Optional Eastmoney financial metric runs fetch latest F10 main financial indicators into `financial_metrics` and derive `financial-metrics-derived-signals`: positive revenue/profit YoY becomes `revenue_growth_up`, while negative growth can become `demand_slowdown`.
- Reports render an optional `Financial Metrics` section when `financial_metrics` is present, including stock, report period, revenue YoY, parent-net-profit YoY, provider, and source URL. This keeps Eastmoney financial-derived signal inputs visible to users instead of only storing them in JSON.
- Optional news evidence runs derive `news_evidence` from Google News RSS titles/snippets and add a non-mock `News Evidence` provider layer named `google-news-rss`. The shared artifact contract is provider-agnostic and includes `query_scope` with requested/queried/omitted narrative IDs. V1 does not parse article bodies and must disclose the title/snippet limitation plus query coverage in reports/source tables.
- Optional news evidence runs also derive `news-derived-signals`: positive snippets become `news_frequency_up`, mixed snippets become `research_mentions_up`, and negative snippets become `language_decay`.

## Mock Scenario Fixtures

- `000001`: AI infrastructure validation scenario, primary stage `strengthening`.
- `000002`: AI power crowding scenario, primary stage `crowded`.
- `000003`: EV pressure and counter-evidence scenario, primary stage `dead`.

## Real Provider Smoke Result

- `161725` with `--provider-mode eastmoney`: Premium Baijiu Consumption / `diverging` in the current fixture-backed mapping layer.
- Real smoke set covers `161725`, `320007`, `003096`, `003834`, `001475`, and `000991`; latest smoke passed the coverage threshold for all six funds and kept calibrated stages `strengthening` / `diverging` / `weakening`.
- Latest registry broadening resolved prior real-smoke gaps for `002594` 比亚迪, `600066` 宇通客车, `603308` 应流股份, `002246` 北化股份, `002572` 索菲亚, `603816` 顾家家居, and `002918` 蒙娜丽莎.
- Latest registry curation replaced 21 clear broad industry-only real-smoke fallback mappings with company-level terms; `600522` 中天科技, `688036` 传音控股, and `688692` 达梦数据 are now explicit excluded candidates for Semiconductor Capex.
- Current multi-match diagnostics flag `300604` 长川科技 as Semiconductor + Defense and `600482` 中国动力 as New Energy + Defense.
- Current excluded mapping candidates are `688036` 传音控股, `688692` 达梦数据, and `600522` 中天科技 as excluded candidates for Semiconductor Capex.
- Current candidate narratives are Consumer Electronics Globalization for `688036`, Domestic Database Infrastructure for `688692`, and Communication And Power Infrastructure for `600522`.
- Latest announcement-evidence probe for `161725` with CNINFO start date `2026-01-01` returned 56 announcements and 56 converted evidence records, while still disclosing the mixed Eastmoney/CNINFO + Mock intelligence foundation as `partial`.
- Latest reviewed-registry enriched acceptance for `161725` passed with no mock provider-foundation layers; effective data quality remains `partial` because registry-rule stock mappings are derived rather than a fully reviewed mapping provider.
- Latest reviewed-mapping enriched acceptance for `161725` passed with all selected mappings using `reviewed_mapping`; `603198` 迎驾贡酒 and `600702` 舍得酒业 were added to the reviewed mapping store to avoid registry-rule fallback.
- Reviewed-store audit metadata is seeded with `review_schema_version=review-metadata-v1` and reviewer `seed-curation` until future web approvals replace it with user-level approval metadata.

## Deferred Scope

- Fully automatic narrative discovery.
- Automatic signal vocabulary governance.
- Full historical replay.
- Complex knowledge graph infrastructure.
- Real-time alerts.
- Frontend workspace, including web-based candidate narrative review and approval.
- Buy / sell signals.

## Current Operating Assumptions

- This project starts with the merged framework scaffold.
- QA/testing workflows are optional, not the default project identity.
- Durable knowledge belongs in project files, not chat history.
- V1 should be monolith-first with clear module boundaries.
- Narrative, Signal, and Evidence are first-class domain objects.
- Slow-changing intelligence should be maintained separately from fast on-demand report generation.
- Human review is required before AI-proposed candidates change core registries.
- Human review will eventually be performed in a web UI; current CLI/report outputs must preserve enough structured state for that future approval workflow.
- Candidate review workflow code should stay pure and immutable so future web endpoints can call it without hidden side effects.
- Review action preview and persistence should use the same action payload contract expected from the future web UI. Preview remains non-persistent; persistence must be explicit and guarded.
- V1 outputs must include version metadata for provider set, narrative registry, signal schema, scoring model, and report template.
- Data provider failures should degrade output quality and confidence instead of crashing the pipeline when mock fallback or partial data is available.
- Mock data and mock fallback must be explicitly disclosed in user-facing report output; no UI or report should present mock-backed analysis as a fully real environment.
- New real intelligence sources should plug into the layer provider interfaces before changing orchestration.
- Real source adapters should use injectable fetchers and return controlled unavailable/partial payloads on provider failure.
- Announcement evidence generation must disclose that V1 classifies metadata only and does not parse source PDFs.
- Optional real announcement runs must add an `Announcements` provider-foundation layer so users can see whether CNINFO data was fresh, partial, or unavailable.
- Optional market quote runs must add a `Market Quotes` provider-foundation layer and preserve provider fallback/degradation events; quote snapshots are artifact/display data only until scoring explicitly consumes them.
- Strict market quote acceptance validates generated artifacts directly: holdings must be fresh Eastmoney data, market quotes must contain real non-mock rows, and remaining registry/mapping/base-evidence/signal layers must disclose `mock://fixtures/...`.
- Derived announcement signals are exposed as `derived_signal_events` in raw/scoring JSON and as a non-mock `Derived Signals` provider layer. Base fixture signals remain present and explicitly mock-backed until a later provider replaces them.
- Market quote derived signals share the same `derived_signal_events` contract and are included in raw `signal_events` plus scoring input. The `Market Quotes` and `Derived Signals` layers stay separate in provider foundation metadata.
- `python scripts/validate_real_enriched_acceptance.py --output-dir outputs/real_enriched_161725` is the strict combined live-provider acceptance command for Eastmoney holdings, CNINFO announcements/evidence, market quotes, and both derived-signal sources. It still requires registry, mapping, base-evidence, and base-signal layers to disclose Mock fixtures. Eastmoney-to-Yahoo quote fallback is allowed only as a recorded and disclosed provider fallback.
- Reviewed-registry workflow data is intentionally separate from `data/fixtures/`. The current store is file-backed so future web approval flows can write reviewed registry snapshots without changing the pipeline contract.
- Reviewed stock mapping workflow data is also separate from `data/fixtures/`. The reviewed mapping store uses `reviewed_mapping` so future web approval screens can distinguish persisted mapping records from runtime registry-term fallback.
- Reviewed stores should fail fast when audit metadata is missing rather than silently presenting fixture-derived data as reviewed.
- Future web source tables should read provider layer `source_url`, `data_quality`, `is_mock`, and optional `review_metadata` directly from generated artifacts.
- Future web data panels should read workspace snapshot `data_layers` for payload availability/count summaries first, then open raw/scoring artifacts only for drill-down payloads.

## Open Questions

- Should the next iteration broaden the narrative registry and rules for more Eastmoney real-fund sectors, or improve the scoring language and report interpretation?
