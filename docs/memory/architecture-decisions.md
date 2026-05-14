# Architecture Decisions

## ADR-0001: Use Merged ECC Framework

- Status: accepted
- Date: 2026-05-12

Decision:

Use a project-local merged framework combining ECC workflow structure, Superpower-inspired execution discipline, and durable memory files.

Rationale:

- The project is new and needs an operating skeleton before implementation work.
- Workflows should be recoverable from files when chat context is gone.
- Agent usage should be deliberate and runtime-checkable.

Consequences:

- Complex work uses `.ecc/runs/<task-run-id>/`.
- Plans live under `docs/exec-plans/active/`.
- Durable project memory lives under `docs/memory/` and `.ecc/memory/project/`.
- QA-specific flows remain available as optional skills.

## ADR-0002: Use Python For V1 Intelligence Engine

- Status: accepted
- Date: 2026-05-13

Decision:

Use Python for the V1 report-first intelligence engine.

Rationale:

- The core work is provider ingestion, structured fixtures, financial data normalization, signal scoring, and report generation.
- Python aligns better with likely future providers and analysis tooling such as AKShare, Tushare, pandas, and financial/statistical workflows.
- V1 does not need a frontend workspace, so starting with Node.js or Next.js would add surface area before the intelligence loop is validated.

Consequences:

- V1 runs as a Python CLI.
- The first acceptance command is `python -m src.main --fund-code 000001`.
- Node.js / Next.js remains a future option for a workspace UI after the report-first engine is stable.

## ADR-0003: Keep Mock Baseline While Adding Eastmoney Holdings Adapter

- Status: accepted
- Date: 2026-05-13

Decision:

Add an explicit `eastmoney` provider mode for no-key Eastmoney/Tiantian Fund holdings while preserving `mock` as the deterministic baseline and keeping `real` as compatibility fallback.

Rationale:

- V1 needs one real holdings path to validate provider boundaries.
- The Eastmoney/Tiantian Fund mobile endpoint can return single-fund stock holdings with holding percentages and public date.
- Real holdings alone are not enough for the full narrative report; registry, stock mapping, evidence, and signals remain local fixtures in V1.
- Mock fixtures must remain stable for repeatable tests and development.

Consequences:

- `python -m src.main --fund-code 161725 --provider-mode eastmoney` can produce a real-holdings-backed report when the public endpoint is reachable.
- If the Eastmoney fetch fails, the adapter records `provider_fallback` and falls back to a mock fixture when available.
- Future real providers should normalize into the same V1 fund-holdings contract before orchestration.

## ADR-0004: Use A Fixed Real-Fund Smoke Set For Provider Regression

- Status: accepted
- Date: 2026-05-13

Decision:

Use a fixed Eastmoney smoke set covering baijiu consumption, semiconductors, healthcare, new energy, defense, and real estate.

Rationale:

- A single real fund is not enough to validate provider normalization, mapping coverage, and report generation.
- The smoke set gives a repeatable check against multiple sector vocabularies while keeping V1 scope small.
- It exposes mapping coverage and unmapped holdings before users trust narrative interpretation.

Consequences:

- `python -m src.main --run-real-smoke` generates per-fund artifacts plus summary JSON/Markdown.
- The smoke set is a regression check, not a recommendation list.
- Registry-term coverage should be expanded only when unmapped holdings reveal a durable narrative gap.

## ADR-0005: Keep Python Quality Gates In Project Metadata

- Status: accepted
- Date: 2026-05-13

Decision:

Declare pytest, ruff, and coverage as project development dependencies and configure their gates in `pyproject.toml`.

Rationale:

- V1 quality checks should be reproducible across machines instead of relying on globally installed Python tools.
- The project already uses Python as the report-first intelligence engine, so Python-native tool configuration belongs beside project metadata.
- An 80% coverage floor matches the ECC testing requirement while keeping the early V1 CLI practical.

Consequences:

- Developers should run `python -m pip install -e ".[dev]"` before local quality checks.
- Standard gates are `python -m ruff check .`, `python -m coverage run -m pytest -q`, `python -m coverage report`, and `python -m compileall -q src tests scripts`.
- Development tool versions are pinned in the `dev` extra until the project introduces a lockfile.
- Coverage is measured over `src`; generated outputs remain ignored.

## ADR-0006: Calibrate Real-Fund Smoke Stages With Local Signals

- Status: accepted
- Date: 2026-05-13

Decision:

Use local V1 signal fixtures and deterministic scoring rules to make the fixed Eastmoney smoke set produce differentiated lifecycle stages.

Rationale:

- The Eastmoney adapter provides live holdings only; narrative registry, evidence, and signals are still fixture-backed in V1.
- A smoke set where every primary narrative is `diverging` proves the pipeline runs but gives weak regression coverage over stage selection.
- Differentiated stages make scoring regressions easier to detect without implying investment advice.

Consequences:

- Current real smoke baseline is `strengthening` for semiconductor and defense, `diverging` for baijiu and healthcare, and `weakening` for new energy and real estate.
- Stage rules now include moderate-strength `strengthening` and weaker-support `weakening` paths.
- Future real signal providers should be validated against this distribution before replacing fixture-backed signals.

## ADR-0007: Disclose Mock And Mixed Provider Foundations In Reports

- Status: accepted
- Date: 2026-05-13

Decision:

Add run-level provider foundation metadata and render a visible `Data Source Notice` in Markdown and HTML whenever a run uses mock data, fallback/degradation, or mixed real/mock provider layers.

Rationale:

- V1 can fetch real Eastmoney holdings while still using fixture-backed registry, stock mappings, evidence, and signals.
- Treating those mixed runs as fully `fresh` would mislead users about the reliability of the report.
- The user-facing report is the place where this distinction must be visible, not only hidden in JSON.

Consequences:

- Raw and scoring JSON include `provider_foundation` with per-layer provenance and `effective_data_quality`.
- Scoring confidence uses `effective_data_quality`; Eastmoney holdings plus mock intelligence layers is `partial`.
- Markdown and HTML reports render a `Data Source Notice` that lists provider layers and degradation events.
- Mock-backed source fields use `mock://fixtures/...` identifiers so source/URL displays do not collapse mock data into a blank source.

## ADR-0008: Split Intelligence Sources Into Layer Provider Interfaces

- Status: accepted
- Date: 2026-05-13

Decision:

Split V1 intelligence data sources into explicit provider-layer interfaces for narrative registry, stock mappings, evidence, signal events, market data, valuation, announcements, and news evidence.

Rationale:

- Eastmoney currently provides holdings only; the intelligence layers remain fixture-backed.
- Future AKShare, Tushare, CNINFO, exchange announcement, and news/search providers should be added behind stable contracts instead of changing orchestration each time.
- Empty mock providers for reserved layers make missing real providers explicit without fabricating data.

Consequences:

- `MockDataProvider` composes `MockIntelligenceProviderSet` for registry, mappings, evidence, and signals.
- Reserved market, valuation, announcement, and news providers return stable empty mock payloads until real providers are implemented.
- Provider foundation can use layer-provider provenance when rendering user-facing data-source disclosure.

## ADR-0009: Add Provider Diagnostics CLI

- Status: accepted
- Date: 2026-05-13

Decision:

Add `python -m src.main --fund-code <code> --provider-diagnostics` to print provider foundation diagnostics as JSON without writing report artifacts.

Rationale:

- Provider state now spans holdings, registry, mappings, evidence, and signals.
- Before connecting real intelligence providers, developers need a cheap way to verify which layers are mock, partial, or degraded.
- Diagnostics should not create user-facing reports or pollute `outputs/`.

Consequences:

- The diagnostics path fetches the fund holdings layer and returns provider foundation metadata only.
- `--provider-mode real --provider-diagnostics` exposes the `provider_fallback` event.
- Future provider work should keep this command stable as a quick source-layer sanity check.

## ADR-0010: Add CNINFO Announcement Adapter As Optional Provider

- Status: accepted
- Date: 2026-05-13

Decision:

Add an optional `CNInfoAnnouncementProvider` adapter for CNINFO announcement metadata, but do not wire it into the default V1 report pipeline yet.

Rationale:

- Announcements are a structured intelligence source and a better first real non-holdings adapter than free-form news.
- V1 still needs deterministic mock behavior by default.
- The adapter should be testable with an injectable fetcher and should fail closed into an unavailable payload.

Consequences:

- CNINFO provider failures record `provider_unavailable` and return empty `unavailable` results.
- The adapter can be used manually or by future orchestration work without changing the current report acceptance path.
- Future announcement-to-evidence conversion should build on this adapter instead of scraping directly inside scoring or report code.

## ADR-0011: Keep Announcement Evidence Conversion Metadata-Only In V1

- Status: accepted
- Date: 2026-05-13

Decision:

Add a deterministic announcement-to-evidence converter that classifies structured announcement metadata into V1 evidence records, but do not parse PDFs or wire the result into default report generation yet.

Rationale:

- CNINFO metadata is enough to test the source-to-evidence contract without adding PDF parsing fragility.
- V1 should not overstate precision from announcement titles alone.
- The converter gives future orchestration a stable boundary between source adapters and scoring/report code.

Consequences:

- Generated evidence confidence combines classification confidence, stock-mapping confidence, and data-quality confidence.
- Generated summaries explicitly state that PDF content has not been parsed.
- Unmapped or malformed announcements are tracked and skipped instead of failing the whole flow.

## ADR-0012: Gate Real Announcement Evidence Behind Explicit CLI Opt-In

- Status: accepted
- Date: 2026-05-13

Decision:

Expose CNINFO announcement evidence through `--include-cninfo-announcements` instead of making real announcement fetching part of the default report pipeline.

Rationale:

- Default V1 runs must stay deterministic and mock-provider first.
- Real announcement metadata can improve evidence density, but it must not be silently mixed into reports.
- Users need a visible provider-foundation layer showing whether announcements were fresh, partial, unavailable, or degraded.

Consequences:

- Default `python -m src.main --fund-code 000001` does not call CNINFO.
- Optional announcement runs include `announcements`, `announcement_evidence`, and an `Announcements` provider layer in output JSON.
- Reports disclose the announcement layer and generated evidence summaries state that PDF content was not parsed.

## ADR-0013: Add CNINFO Selector Fix And Announcement Evidence Smoke

- Status: accepted
- Date: 2026-05-13

Decision:

Use CNINFO `stock` selectors in `code,orgId` form for Shanghai and Shenzhen A-shares, and add `python -m src.main --run-announcement-smoke` as a live regression check for optional announcement evidence.

Rationale:

- CNINFO can return zero results when the announcement query sends only the 6-digit stock code for Shanghai/Shenzhen A-shares.
- A live optional announcement path needs more than a unit test because selector behavior and provider availability are external interface risks.
- The user-facing mixed/mock data-source notice must remain visible whenever real CNINFO data is combined with fixture-backed intelligence layers.

Consequences:

- `CNInfoAnnouncementProvider` builds selectors such as `600519,gssh0600519` and `000001,gssz0000001`.
- `python -m src.main --run-announcement-smoke` runs the `161725` Eastmoney + CNINFO path and writes `announcement_evidence_smoke_summary.json` and `.md`.
- The smoke fails if announcements are empty, evidence conversion is empty, the `Announcements` provider layer is missing or mock, or the data-source notice does not disclose mixed/mock output.

## ADR-0014: Lower Confidence For Multi-Match Fallback Mappings

- Status: accepted
- Date: 2026-05-13

Decision:

Retain multi-match `registry_term_rule` mappings, but lower their confidence and emit review flags instead of deleting or silently accepting them as ordinary fallback matches.

Rationale:

- Some companies are genuinely cross-domain, so deleting one of the mappings would be too aggressive without manual review.
- Full mapping coverage can hide precision risk if one holding contributes to multiple narratives through broad registry terms.
- Downstream scoring should see lower confidence for ambiguous fallback mappings, and reports should make the ambiguity visible.

Consequences:

- A single fallback match keeps confidence `0.52`.
- A multi-match fallback lowers each affected mapping to confidence `0.42`.
- Affected mappings carry `needs_review` and `precision_flag`.
- Raw/scoring JSON and reports include `mapping_precision_flags` for user-visible review.

## ADR-0015: Emit Mapping Rationales With Stock Narrative Mappings

- Status: accepted
- Date: 2026-05-13

Decision:

Emit `mapping_rationales` for every selected stock-to-narrative mapping in raw/scoring JSON and Markdown/HTML reports.

Rationale:

- Users need to know why a stock belongs to a narrative, especially when V1 combines explicit fixture mappings with broad registry-term fallback rules.
- Mapping coverage alone can hide weak explanations; a holding matched by industry term should be visibly different from one matched by an explicit curated mapping.
- The rationale object gives future UI and manual-review workflows a stable structure without changing scoring contracts.

Consequences:

- Fixture mappings are reported as explicit stock-narrative fixture rules.
- Registry-term fallback mappings list matched terms from stock code, stock name, or industry.
- Multi-match fallback rationales preserve `needs_review` and `precision_flag` so ambiguous mappings remain visible in user-facing output.

## ADR-0016: Flag Broad Industry-Only Fallback Mappings

- Status: accepted
- Date: 2026-05-14

Decision:

Treat single `registry_term_rule` mappings supported only by holding industry terms as lower-precision fallback mappings.

Rationale:

- Broad industry terms such as `电子` or `军工` are useful for coverage, but they are weaker evidence than stock-name, product, or company-specific registry terms.
- V1 should preserve these mappings for continuity while preventing users from confusing broad sector coverage with a curated stock-level narrative relationship.
- The mapping precision output should support later registry curation without changing the scoring pipeline shape.

Consequences:

- Single broad industry-only fallback confidence is lowered from `0.52` to `0.48`.
- The mapping carries `needs_review` and `precision_flag: broad_industry_fallback`.
- Raw/scoring JSON and reports include a `mapping_precision_flags` row with `recommended_action: curation_review`.
- Multi-match fallback remains the higher-priority precision flag when one holding maps to multiple narratives.

## ADR-0017: Curate Clear Real-Smoke Broad Fallbacks With Company Terms

- Status: accepted
- Date: 2026-05-14

Decision:

Add company-level registry terms for clear real-smoke broad industry-only fallback mappings, but leave ambiguous mappings flagged instead of forcing them into the current narrative.

Rationale:

- `broad_industry_fallback` rows are useful curation work items, not an automatic instruction to expand every narrative.
- Clear cases such as baijiu producers, innovative drug companies, defense aerospace companies, new energy equipment suppliers, real estate chain companies, and semiconductor equipment/EDA companies can be made more precise with company-level terms.
- Ambiguous cases should stay visible for narrative reassessment rather than contaminating a registry with questionable stock-to-narrative claims.

Consequences:

- The real-smoke broad fallback count is reduced from 24 to 3 after adding company-level terms.
- Remaining broad flags are currently `600522` 中天科技, `688036` 传音控股, and `688692` 达梦数据 under Semiconductor Capex mapping rules.
- Future curation should decide whether these need a different narrative, an exclusion, or a separate technology/software narrative.

## ADR-0018: Aggregate Mapping Precision Flags In Real-Smoke Summaries

- Status: accepted
- Date: 2026-05-14

Decision:

Include per-fund `mapping_precision_flags` in real-smoke summary JSON and render them in the Markdown summary.

Rationale:

- The fixed real-smoke set is the main regression surface for registry coverage and precision.
- Precision flags are curation work items; burying them in individual fund reports makes follow-up slower.
- Summary-level aggregation keeps mapping gaps, multi-mapped holdings, and broad-industry flags in one review surface.

Consequences:

- Each fund result includes `mapping_precision_flag_count` and `mapping_precision_flags`.
- `real_fund_smoke_summary.md` includes a `Mapping Precision Flags` section when any fund emits flags.
- Registry curation can be driven from one summary artifact after smoke runs.

## ADR-0019: Show Precision Flag Counts In Real-Smoke CLI Output

- Status: accepted
- Date: 2026-05-14

Decision:

Print `precision_flags=<count>` for each fund in `python -m src.main --run-real-smoke` output.

Rationale:

- The terminal smoke output is often the first thing a developer or CI log reader sees.
- Coverage can be 100% while precision flags still indicate registry curation work.
- Surfacing the count keeps quick checks aligned with the richer summary artifacts.

Consequences:

- Existing per-fund smoke output keeps fund code, scenario, primary narrative, stage, and coverage.
- Missing precision count fields default to `0` for compatibility.

## ADR-0020: Exclude Known-Bad Fallback Mapping Candidates

- Status: accepted
- Date: 2026-05-14

Decision:

Add explicit mapping exclusions for known-bad fallback candidates, and emit excluded candidates in JSON, reports, real-smoke summaries, and CLI output counts.

Rationale:

- Some broad industry fallback candidates are clearly not valid for the candidate narrative, but adding a replacement narrative immediately would change the taxonomy.
- Excluding known-bad candidates prevents incorrect narrative exposure from entering aggregation and scoring while preserving a review trail.
- Exclusions should be transparent to users and developers; an unmapped holding should show whether it was unmapped because a candidate was intentionally blocked.

Consequences:

- `mapping_exclusions.json` stores reviewed stock/narrative/method exclusions and reasons.
- Exclusions apply to fallback candidates only, not explicit curated fixture mappings.
- Excluded candidates are omitted from `stock_narrative_mappings`, then emitted as `excluded_mapping_candidates`.
- Real-smoke summary JSON/Markdown includes excluded candidates, and CLI output includes `excluded_candidates=<count>`.

## ADR-0021: Keep Candidate Narratives Review-Only

- Status: accepted
- Date: 2026-05-14

Decision:

Store candidate narratives in the registry and emit only the candidates related to current exclusions, without using them for active mapping, aggregation, or scoring.

Rationale:

- Exclusions identify taxonomy gaps, but immediately promoting new narratives would change the product interpretation layer without human review.
- Candidate narratives give users and maintainers a concrete answer to "what might this stock belong to?" while keeping the scored report conservative.
- Linking candidates to `related_exclusion_ids` and `triggering_stock_codes` makes the review trail reproducible from raw output.

Consequences:

- `candidate_narratives` is validated as part of `narrative_registry.json`.
- Raw/scoring JSON and reports include in-scope candidate narratives when related exclusions are present.
- Candidate narratives do not enter `stock_narrative_mappings`, `all_narratives`, primary/secondary narrative selection, or lifecycle scoring.
- Real-smoke summaries and CLI output include candidate narrative counts for taxonomy-review visibility.

## ADR-0022: Preserve Future Web Approval Workflow Shape

- Status: accepted
- Date: 2026-05-14

Decision:

Do not build the web review UI in V1, but shape candidate narrative and exclusion outputs so a future web workspace can display, approve, reject, or defer them without reworking the core data contracts.

Rationale:

- The intended long-term workflow is visual: users review candidate narratives and approval decisions in a web interface.
- Building the UI before the intelligence contracts stabilize would add premature surface area.
- Stable structured objects now prevent report-only prose from becoming a migration blocker later.

Consequences:

- Candidate and exclusion records should keep stable IDs, status fields, rationale, source, related stock/exclusion links, reviewer metadata, and timestamps.
- CLI and report outputs remain the current interface, but JSON must be workspace-ready.
- Promotion from candidate to active narrative remains a human approval action, not automatic scoring behavior.

## ADR-0023: Use Explicit Immutable Candidate Review Actions

- Status: accepted
- Date: 2026-05-14

Decision:

Represent candidate narrative approval as explicit immutable review actions supporting `approve`, `reject`, and `defer`.

Rationale:

- Future web approval screens need a deterministic backend contract that can be tested before the UI exists.
- Approval has higher risk than report rendering because it can change the active taxonomy.
- A pure function makes review actions auditable and avoids hidden mutation of the registry fixture or future persistence layer.

Consequences:

- `approve` requires promotion metadata and appends a new active narrative while marking the candidate as promoted/approved.
- `reject` and `defer` update candidate review state only and do not change active narratives.
- Default report generation does not call the review-action workflow.
- Future persistence/API work can wrap the pure function rather than reimplementing promotion semantics.

## ADR-0024: Emit Candidate Review Queue For Future Web Workspace

- Status: accepted
- Date: 2026-05-14

Decision:

Emit a `candidate_review_queue` object in raw/scoring outputs for in-scope candidate narratives.

Rationale:

- Future web approval screens need a single queue-shaped object rather than reconstructing work items from reports.
- The queue should connect candidates, exclusions, available actions, and an approval action template.
- Emitting a queue now validates the data contract without building UI or persistence early.

Consequences:

- Queue items are read-ready and deterministic.
- Queue emission does not persist actions, call promotion, or change scoring.
- Real-smoke summaries include queue item counts so taxonomy-review workload remains visible in CLI and CI output.

## ADR-0025: Write Dedicated Review Queue Artifact

- Status: accepted
- Date: 2026-05-14

Decision:

Write `fund_<code>_review_queue.json` beside raw, scoring, Markdown, and HTML artifacts.

Rationale:

- A future web approval workspace should not have to parse full raw/scoring snapshots to load review work.
- Keeping a dedicated artifact makes the queue contract easier to test and preserve.
- The artifact remains read-only and does not imply persistence of review decisions.

Consequences:

- `run_pipeline` returns a `review_queue` artifact path.
- The artifact includes metadata, fund identity, provider foundation, queue items, candidate narratives, and excluded mapping candidates.
- Review queue artifacts can be validated directly through the CLI before future web workspace loading.
- Existing raw/scoring queue fields remain for snapshot reproducibility.

## ADR-0026: Preview Review Actions Before Registry Persistence

- Status: accepted
- Date: 2026-05-14

Decision:

Add a CLI-backed review-action preview wrapper that reads the same JSON action
payload future web approval screens will submit, applies it to a registry copy,
and writes a preview artifact without mutating the source registry.

Rationale:

- The project needs a concrete backend contract before building the web approval workspace.
- Candidate promotion changes taxonomy state, so local preview must stay separate from persistence.
- Reusing the same action payload shape avoids inventing a different CLI-only workflow.

Consequences:

- `python -m src.main --preview-review-action <action.json>` does not require `--fund-code`.
- Preview output includes the original action, summary, mutation-safety metadata, `registry_delta`, and result registry.
- The source registry fixture is never written by this command; explicit output paths must stay inside `--output-dir` and must not overwrite registry/action inputs.
- Preview artifacts are contract-validated before they are written.
- Preview artifacts can also be validated directly through the CLI without applying or persisting a review action.
- Future persistence/API work must be explicit.

## ADR-0027: Require Explicit Registry Persistence For Review Actions

- Status: accepted
- Date: 2026-05-14

Decision:

Add a separate review-action persistence command that writes the reviewed
registry result to an explicit registry output path. In-place registry overwrite
is rejected unless explicitly allowed.

Rationale:

- Preview and persistence have different risk profiles and should not share one
  ambiguous command.
- Future web approval screens need a backend persistence boundary that reuses
  the same action payload and validation contract.
- Registry updates change taxonomy state, so accidental fixture mutation must be
  guarded.

Consequences:

- `python -m src.main --persist-review-action <action.json> --registry-output <registry.next.json>` does not require `--fund-code`.
- The persistence path validates the preview and final registry before writing.
- The action input file cannot be overwritten.
- Existing non-source output files cannot be overwritten unless `--allow-registry-output-overwrite` is present.
- Persistence writes a separate result artifact by default so registry updates have an audit record outside the registry file.
- Direct persistence callers must supply an audit output location; registry and audit writes use rollback so audit failure does not leave an unaudited registry output.
- Persistence result artifacts record the overwrite policy flags used for the write.
- Persistence result artifacts are contract-validated before write.
- Persistence result artifacts can also be validated directly through the CLI without running a fund report.
- In-place registry overwrite requires `--allow-registry-overwrite`.
- Normal report generation never calls review-action persistence.

## ADR-0028: Write Pipeline Artifact Manifest For Web Loading

- Status: accepted
- Date: 2026-05-14

Decision:

Write `fund_<code>_manifest.json` beside raw, scoring, review queue, Markdown,
and HTML artifacts.

Rationale:

- A future web workspace should discover run outputs from one small contract
  rather than reconstructing filenames.
- The manifest can expose data quality, provider foundation, and degradation
  events before the web UI loads larger payloads.
- Relative artifact names keep local outputs portable across output directories.

Consequences:

- `run_pipeline` returns a `manifest` artifact path.
- Manifest artifacts include raw, scoring, review queue, Markdown, and HTML paths.
- Manifest artifacts can be validated directly through the CLI before future web workspace loading.
- Generated artifact directories can be validated through one CLI command before a future web workspace loads them.
- Existing artifact names and payload contracts remain unchanged.

## ADR-0029: Add Strict Eastmoney Real Holdings Acceptance

- Status: accepted
- Date: 2026-05-14

Decision:

Add `scripts/validate_real_holdings_acceptance.py` as a manual live-provider
acceptance command for fund `161725`.

Rationale:

- V1 is now reducing mock surface one layer at a time, starting with fund
  holdings.
- The normal `eastmoney` run can degrade to mock when the provider is
  unavailable, but acceptance needs to prove that live holdings actually arrived.
- Future web loading depends on the same raw, scoring, review queue, manifest,
  Markdown, and HTML artifacts being internally consistent.

Consequences:

- The script runs `--provider-mode eastmoney`, validates artifact contracts, and
  then rejects any fallback to mock holdings.
- Registry, stock mappings, evidence, and signals intentionally remain
  mock-backed in this check, so overall quality is `partial`.
- Markdown and HTML reports must disclose mixed Eastmoney and Mock fixture data.
- The command remains outside CI because it depends on live network and provider
  availability.

## ADR-0030: Add Strict CNINFO Announcement Acceptance

- Status: accepted
- Date: 2026-05-14

Decision:

Add `scripts/validate_announcement_acceptance.py` as a manual live-provider
acceptance command for the optional Eastmoney + CNINFO report path.

Rationale:

- The project is reducing mock layers incrementally and needs a strict check for
  the first real evidence source.
- The existing announcement smoke summary proves the high-level case, but future
  web loading also depends on raw, scoring, review queue, manifest, Markdown,
  and HTML artifacts preserving the same provider foundation.
- CNINFO metadata is real provider data, but V1 only classifies metadata and does
  not parse source PDFs, so the report must disclose this mixed foundation.

Consequences:

- The script runs `--include-cninfo-announcements`, validates artifact contracts,
  and rejects missing CNINFO announcements or generated announcement evidence.
- Eastmoney holdings and CNINFO announcements must be non-mock; registry,
  mappings, base evidence, and signals remain mock-backed.
- The command remains outside CI because it depends on live provider
  availability.

## ADR-0031: Add Optional Market Quote Snapshot Layer

- Status: accepted
- Date: 2026-05-14

Decision:

Add an optional `--include-market-quotes` path that writes current holding quote
snapshots into raw and scoring artifacts and adds a `Market Quotes` provider
layer.

Rationale:

- Quote data is a natural next non-mock layer after holdings and announcement
  metadata, but V1 scoring should not silently change until the scoring model is
  explicitly recalibrated.
- Eastmoney quote endpoints can be intermittently unavailable, so a Yahoo chart
  fallback keeps the server-side artifact path useful without requiring API
  credentials.
- Future web screens need the quote source and fallback state in structured
  provider-foundation metadata.

Consequences:

- Quote snapshots are generated only when requested.
- Raw and scoring JSON include `market_quotes`; reports disclose the quote
  provider layer.
- Quote provider failures record degradation events and lower effective data
  quality instead of crashing the run.
- V1 scoring remains driven by existing signal events until a later scoring
  calibration explicitly consumes quote data.

## ADR-0032: Add Strict Market Quote Acceptance

- Status: accepted
- Date: 2026-05-14

Decision:

Add `scripts/validate_market_quotes_acceptance.py` as a manual live-provider
acceptance command for the optional quote snapshot path.

Rationale:

- Quote snapshots are useful for future web display only if they are generated
  as structured, non-mock artifacts.
- The normal quote path can degrade or fallback by provider, but acceptance
  should prove that at least one real quote row is present.
- The same raw, scoring, review queue, manifest, Markdown, and HTML bundle must
  remain web-loadable after quote data is added.

Consequences:

- The script runs `--include-market-quotes`, validates artifact contracts, and
  rejects missing or mock quote rows.
- Eastmoney holdings remain strict and fresh.
- Registry, mappings, base evidence, and signals intentionally remain
  mock-backed in this check.
- The command remains outside CI because it depends on live provider
  availability.

## ADR-0033: Derive Scoring Signals From CNINFO Announcement Evidence

- Status: accepted
- Date: 2026-05-14

Decision:

When `--include-cninfo-announcements` is enabled, convert generated CNINFO
announcement evidence into traceable `derived_signal_events` and include those
events in narrative scoring.

Rationale:

- Real announcement evidence should not remain report-only once the evidence
  path is stable.
- The first scoring integration should be conservative and inspectable, not a
  broad model recalibration.
- Future web source tables need to distinguish fixture base signals from
  provider-derived signals.

Consequences:

- Positive earnings, order, and capital-flow announcements become V1 support
  signal types.
- Negative risk announcements become counter-evidence risk signals.
- Mixed financial and governance disclosures become low-weight momentum signals.
- Raw and scoring artifacts include `derived_signal_events`.
- Provider foundation adds a non-mock `Derived Signals` layer while the base
  `Signals` layer remains mock-backed.

## ADR-0034: Derive Scoring Signals From Market Quote Snapshots

- Status: accepted
- Date: 2026-05-14

Decision:

When `--include-market-quotes` is enabled, convert market quote change
percentages into conservative relative-strength signal events and include those
events in narrative scoring.

Rationale:

- Quote snapshots should become more than display-only once their artifact path
  and acceptance gate are stable.
- Relative strength is a narrow, inspectable first signal from price data.
- Negative quote movement needs a scoring vocabulary entry, so
  `relative_strength_down` is added to capital-score negatives.

Consequences:

- Positive quote changes become `relative_strength_up`.
- Negative quote changes become `relative_strength_down`.
- Raw and scoring artifacts include quote-derived events in
  `derived_signal_events`.
- Raw `signal_events` and scoring input include both fixture signals and
  derived quote signals.
- Provider foundation keeps `Market Quotes` and `Derived Signals` as separate
  non-mock layers while base `Signals` remains mock-backed.

## ADR-0035: Add Strict Combined Real Enriched Acceptance

- Status: accepted
- Date: 2026-05-14

Decision:

Add `scripts/validate_real_enriched_acceptance.py` as the manual acceptance
gate for the combined optional real-provider path.

Rationale:

- Separate holdings, announcement, and market quote checks prove individual
  adapters, but future server and web flows need the whole enriched artifact
  bundle to run together.
- The acceptance contract must keep users informed when a report mixes real
  provider data with fixture-backed intelligence layers.
- Derived signals should be traceable to both CNINFO announcement evidence and
  market quote snapshots before more mock layers are removed.

Consequences:

- The command runs Eastmoney holdings, CNINFO announcements, market quotes, and
  artifact contract validation.
- It rejects missing announcement evidence, missing quote rows, missing derived
  signal sources, mock real-provider layers, and hidden Mock fixture disclosure.
- Eastmoney-to-Yahoo quote fallback is allowed only as a recorded and disclosed
  provider fallback because the Eastmoney quote endpoint is intermittently
  unavailable.
- Registry, mappings, base evidence, and base signals intentionally remain
  mock-backed in this acceptance until later provider work replaces them.
- The command remains outside CI because it depends on live provider
  availability.

## ADR-0036: Add Optional Registry-Rule Stock Mapping Mode

- Status: accepted
- Date: 2026-05-14

Decision:

Add `--stock-mapping-mode registry-rule` for single report runs.

Rationale:

- Users need to see why a holding maps to a narrative without treating static
  fixture mappings as the only source of truth.
- The existing registry-term fallback can be promoted into an explicit optional
  mapping mode without changing default behavior.
- Future web approval flows need a clean distinction between mapping generated
  by runtime rules and mapping asserted by a static fixture.

Consequences:

- Default runs still use explicit fixture mappings plus registry-rule fallback.
- Registry-rule mode skips `stock_narrative_mappings.json` and derives selected
  mappings from holdings and Narrative Registry aliases/terms only.
- Raw and scoring artifacts include `stock_mapping_mode`.
- Provider foundation marks `Stock Mappings` as
  `registry-rule-stock-mapping` in registry-rule mode.
- Fully mock-backed registry-rule runs remain `mock`; runtime mapping does not
  upgrade mock inputs into mixed real data.
- The CLI accepts registry-rule mode only for single `--fund-code` report runs;
  diagnostics, batch/smoke, validation, and review-action commands reject it
  instead of silently ignoring it.
- The Narrative Registry layer remains Mock-backed and must still be disclosed
  until a real registry store replaces the fixture.

## ADR-0037: Add Strict Registry-Rule Enriched Acceptance

- Status: accepted
- Date: 2026-05-14

Decision:

Add `scripts/validate_registry_rule_enriched_acceptance.py` as a manual
live-provider acceptance gate for the enriched path with
`--stock-mapping-mode registry-rule`.

Rationale:

- The project needs a concrete end-to-end proof that a real fund can run
  without static stock mapping fixtures.
- Registry-rule mapping is still registry-dependent, so the acceptance must
  preserve Mock disclosure for the registry while proving the stock mapping
  layer itself is runtime-derived.
- This is a bridge toward replacing fixture mapping with a service-backed
  mapping provider and future web approval flows.

Consequences:

- The command reuses the strict real-enriched acceptance contract.
- It rejects static `fixture_rule` selected mappings.
- It requires `stock_mapping_mode=registry-rule`, `registry_term_rule` mapping
  methods, and a `registry-rule-stock-mapping` provider layer.
- It remains outside CI because it depends on live provider availability.

## ADR-0038: Add Optional Provider-Derived Base Intelligence Mode

- Status: accepted
- Date: 2026-05-14

Decision:

Add `--base-intelligence-mode provider-derived` for single enriched report runs
and `scripts/validate_provider_derived_enriched_acceptance.py` as its strict
manual live acceptance gate.

Rationale:

- After holdings, announcements, market quotes, derived signals, and
  registry-rule stock mappings are available, base evidence and signal fixtures
  are the next mock layers to remove.
- The first removal path should be opt-in and acceptance-gated so default V1
  behavior remains stable.
- Future web source tables need evidence and signal inputs that can be loaded
  without guessing whether fixture data leaked into a provider-derived run.

Consequences:

- Default runs still use fixture evidence and signals.
- Provider-derived mode requires CNINFO announcements.
- Raw `evidence` equals generated announcement evidence.
- Raw `signal_events` equals `derived_signal_events`.
- Provider foundation marks `Evidence` as `provider-derived-evidence` and
  `Signals` as `provider-derived-signals`.
- The Narrative Registry remains Mock-backed and visibly disclosed until a real
  registry store replaces it.

## ADR-0039: Add File-Backed Reviewed Narrative Registry Store

- Status: accepted
- Date: 2026-05-15

Decision:

Add `--narrative-registry-mode reviewed` for single report runs, backed by
`data/registry/narrative_registry.reviewed.json`, and add
`scripts/validate_reviewed_registry_enriched_acceptance.py` as the strict manual
live acceptance gate for the enriched reviewed-registry path.

Rationale:

- The Narrative Registry changes slowly and should be separated from fixture
  data before a web approval workflow exists.
- A file-backed reviewed-registry store gives the future web UI a durable read/write
  target while keeping the current CLI/report pipeline simple.
- Reviewed registry provenance must appear as a non-mock provider layer so users
  are not told that approved registry data came from Mock fixtures.

Consequences:

- Default runs still use the fixture-backed registry.
- Reviewed mode validates the registry payload before orchestration and returns
  deep copies to avoid hidden mutation.
- Raw and scoring artifacts include `narrative_registry_mode`.
- Provider foundation marks `Narrative Registry` as
  `reviewed-registry-store` with `reviewed-registry://...#sha256=...` source
  URLs so same-basename registry snapshots remain distinguishable.
- `--narrative-registry-path` requires reviewed mode and is rejected for
  diagnostics, batch/smoke, validation, and review-action commands.
- The reviewed-registry enriched acceptance path now runs without mock
  provider-foundation layers; effective data quality remains `partial` until
  stock mappings become a fully reviewed provider/service.
