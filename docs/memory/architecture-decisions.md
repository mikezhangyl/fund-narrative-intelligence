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

## ADR-0040: Add File-Backed Reviewed Stock Mapping Store

- Status: accepted
- Date: 2026-05-15

Decision:

Add `--stock-mapping-mode reviewed` for single report runs, backed by
`data/registry/stock_narrative_mappings.reviewed.json`, and add
`scripts/validate_reviewed_mapping_enriched_acceptance.py` as the strict manual
live acceptance gate for the enriched reviewed-mapping path.

Rationale:

- Runtime registry-rule mappings explain why a holding matched a narrative, but
  they are still generated at report time and need review flags for ambiguous
  cases.
- Future web approval workflows need an explicit persisted mapping store where
  approved stock-to-narrative relationships can live independently from static
  fixtures.
- Reports and artifacts need to distinguish reviewed mappings from
  `fixture_rule` and `registry_term_rule` mappings.

Consequences:

- Default runs still use fixture mappings.
- Registry-rule mode remains available for discovery and gap-filling.
- Reviewed mode validates the mapping payload before orchestration and returns
  deep copies to avoid hidden mutation.
- Raw and scoring artifacts continue to include `stock_mapping_mode`.
- Provider foundation marks `Stock Mappings` as `reviewed-mapping-store` with
  `reviewed-mapping://...#sha256=...` source URLs.
- `--stock-mappings-path` requires reviewed mode and is rejected for
  diagnostics, batch/smoke, validation, and review-action commands.
- The reviewed-mapping enriched acceptance path rejects selected mappings with
  `fixture_rule` or `registry_term_rule`.

## ADR-0041: Require Audit Metadata in Reviewed Stores

- Status: accepted
- Date: 2026-05-15

Decision:

Require reviewed registry and reviewed mapping stores to include store-level
`review_metadata`, and require reviewed entries to carry entry-level approval
metadata.

Rationale:

- Future web approval screens need to display who approved a registry or mapping
  entry and when.
- A file being stored under `data/registry/` is not enough to prove review
  status.
- Provider validation should fail fast when reviewed-store provenance is missing
  instead of letting reports overstate approval quality.

Consequences:

- Reviewed registry active narratives must have non-empty `reviewed_by` and
  `reviewed_at`.
- Reviewed mapping rows must include `review.status=approved`, `reviewed_by`,
  and `reviewed_at`.
- Reviewed mapping live acceptance validates the source store metadata before
  validating generated artifacts.
- Mock fixtures remain unchanged; audit metadata is required only for reviewed
  store providers.

## ADR-0042: Preserve Review Metadata in Provider Foundation Layers

- Status: accepted
- Date: 2026-05-15

Decision:

Preserve optional `review_metadata` on normalized provider-foundation layers and
emit reviewed registry/mapping store metadata through generated artifacts.

Rationale:

- Future web source tables should not need to reopen or parse reviewed store
  files to show approval provenance.
- Provider foundation is already the shared source-of-truth object across raw,
  scoring, review queue, manifest, and reports.
- Keeping metadata optional avoids imposing reviewed-store fields on mock and
  live market/announcement providers.

Consequences:

- Reviewed registry and stock mapping provider layers include store-level
  `review_metadata`.
- Provider foundation normalization preserves `review_metadata` when present.
- Reviewed-mapping acceptance now verifies emitted provider-foundation layer
  metadata in addition to validating source store metadata.
- Non-reviewed providers remain unchanged.

## ADR-0043: Emit Source Table Artifact

- Status: accepted
- Date: 2026-05-15

Decision:

Write `fund_<code>_source_table.json` beside raw, scoring, review queue,
manifest, Markdown, and HTML artifacts.

Rationale:

- The future web workspace will render source/provenance tables and approval
  context visually, so it needs stable rows that do not require parsing reports.
- Provider foundation already normalizes source URLs, mock flags, data quality,
  degradation events, and optional reviewed-store metadata.
- A dedicated artifact gives `--validate-artifact-contracts` a clear contract
  to protect before web loading exists.

Consequences:

- The manifest includes `source_table` with JSON format metadata.
- The source table carries `fund_code` and `as_of_date`; manifest bundle
  validation rejects identity drift.
- Source-table validation rejects malformed `provider_foundation.layers`,
  duplicate layer names, layer/foundation drift, and degradation-event drift.
- V1 still performs approvals through CLI/file artifacts only; web interaction
  remains a later slice.

## ADR-0044: Add Workspace Snapshot Loader Contract

- Status: accepted
- Date: 2026-05-15

Decision:

Add a build/validate CLI for `fund_<code>_workspace_snapshot.json`.

Rationale:

- Future web screens should not have to rediscover generated artifacts or
  duplicate backend bundle-joining logic.
- The current artifact family already contains the data needed for a read-only
  approval/source workspace: manifest, source table, review queue, scoring
  narratives, and report links.
- A server-side snapshot contract lets us validate web-readiness before adding
  Next.js or browser interaction.

Consequences:

- `--build-workspace-snapshot` accepts a manifest file or single-manifest output
  directory and writes the snapshot beside the bundle by default.
- `--validate-workspace-snapshot` validates identity, provider foundation,
  source-table, review-queue, report, narrative, and approval-workflow fields.
- The snapshot marks `approval_workflow.status = ready_for_future_web`, but
  remains read-only; existing preview/persist CLI commands still own mutations.

## ADR-0045: Add Quote-Derived Valuation Context

- Status: accepted
- Date: 2026-05-15

Decision:

Add `--include-valuation-snapshots` as an optional layer that derives
`valuation_snapshots` from market quote payloads.

Rationale:

- Valuation is a planned V1 dimension, but full financial valuation feeds require
  Tushare, AKShare, or report parsing that is not wired yet.
- A quote-derived context layer lets the service exercise valuation artifact and
  source-table plumbing without pretending it has full fundamental valuation.
- The feature requires `--include-market-quotes`, so it only runs when there is
  a concrete quote source to cite.

Consequences:

- Raw and scoring artifacts include `valuation_snapshots` only when explicitly
  requested.
- Provider foundation includes a `Valuation` layer with provider
  `quote-derived-valuation`.
- The payload carries `valuation_basis = quote_derived_context` to prevent
  overclaiming.
- Scoring weights are unchanged in this slice.

## ADR-0046: Add RSS-Derived News Evidence As Optional Layer

- Status: accepted
- Date: 2026-05-15

Decision:

Add optional `google-news-rss` evidence ingestion for mapped narratives before
introducing paid search/news APIs.

Rationale:

- News and market language is a documented data-source layer, but V1 should not
  require API credentials or silently scrape article bodies.
- RSS title/snippet evidence provides an end-to-end provider surface that can
  reduce mock usage while staying honest about source depth.
- The future web workspace needs source-table-ready provider metadata for this
  layer even before a UI exists.

Consequences:

- `--include-news-evidence` adds `news_evidence` to raw/scoring artifacts and a
  `News Evidence` provider-foundation/source-table layer.
- The artifact contract is provider-agnostic and includes `query_scope` with
  requested, queried, and omitted narrative IDs.
- Provider failures degrade to `unavailable` payloads with degradation events.
- Reports/source tables must state that V1 classifies RSS titles/snippets only
  and does not parse article bodies, plus the queried narrative coverage.

## ADR-0047: Derive Momentum Signals From News Evidence

- Status: accepted
- Date: 2026-05-15

Decision:

Convert optional `news_evidence` into deterministic `news-derived-signals` that
feed the existing scoring dimensions.

Rationale:

- News ingestion should affect narrative state, not only report evidence
  density.
- The scoring model already has momentum signal types for news frequency,
  research mentions, and language decay.
- Keeping derivation deterministic avoids LLM-based sentiment drift while still
  reducing fixture-signal dependency.

Consequences:

- Positive news snippets become `news_frequency_up`.
- Mixed news snippets become `research_mentions_up`.
- Negative news snippets become `language_decay`.
- `Derived Signals` provider foundation can now report `news-derived-signals`
  or `mixed-derived-signals` when combined with CNINFO/market quote signals.

## ADR-0048: Add Explicit Eastmoney Valuation Metrics Source

- Status: accepted
- Date: 2026-05-15

Decision:

Add an explicit `--valuation-source eastmoney` option that fetches Eastmoney
quote-detail valuation metrics into the existing `valuation-snapshot-v1`
contract.

Rationale:

- The existing `--include-valuation-snapshots` default is documented as
  quote-derived context, and changing that default would blur backwards
  compatibility.
- Eastmoney can provide PE/PB/market-cap-style metrics without credentials,
  which reduces the placeholder surface for the valuation dimension.
- The payload must still avoid overclaiming: Eastmoney quote-detail metrics are
  not a full financial statement feed or historical valuation percentile model.

Consequences:

- `valuation-snapshot-v1` now accepts both `quote-derived-valuation` with
  `valuation_basis = quote_derived_context` and `eastmoney-valuation` with
  `valuation_basis = provider_valuation_metrics`.
- Reviewed-mapping enriched acceptance uses `--valuation-source eastmoney`.
- Reports and source tables disclose the Eastmoney valuation provider note.
- Scoring weights remain unchanged until a later valuation-scoring calibration
  slice consumes the richer metrics.

## ADR-0049: Derive Valuation Risk Signals From Provider Valuation Metrics

- Status: accepted
- Date: 2026-05-15

Decision:

Convert Eastmoney provider valuation snapshots into deterministic
`valuation-derived-signals` before scoring, instead of reading valuation
snapshots directly inside the scoring engine.

Rationale:

- The scoring model is intentionally signal-driven across all dimensions.
- Keeping valuation as derived signal events preserves source provenance,
  stock-level mapping, and future web traceability.
- Restricting derivation to `provider_valuation_metrics` avoids treating
  quote-derived context as a full valuation source.

Consequences:

- Elevated provider valuation metrics become `valuation_extreme` signals.
- Discounted provider valuation metrics become `valuation_reset` signals.
- Raw/scoring artifacts include these valuation signals in both
  `derived_signal_events` and scoring `signal_events`.
- Reviewed-mapping enriched acceptance now requires Eastmoney valuation
  snapshots to produce valuation-derived signals.

## ADR-0050: Emit Signal Trace Artifact For Score Provenance

- Status: accepted
- Date: 2026-05-15

Decision:

Emit a dedicated `fund_<code>_signal_trace.json` artifact and include it in the
artifact manifest and workspace snapshot.

Rationale:

- Future web screens need to explain score provenance without recomputing joins
  from raw/scoring JSON.
- Source tables explain provider layers, but they do not show which signal
  events affected which scoring dimensions.
- A separate contract keeps reports presentational while preserving a
  machine-readable trace for UI inspection and approval workflows.

Consequences:

- Signal trace artifacts include per-narrative dimension traces with signal ID,
  signal type, role, source provider, source URL, source layer, and mock status.
- `--validate-artifact-contracts` validates signal trace artifacts when present
  and manifest-referenced signal traces for identity/provider-foundation drift.
- Workspace snapshots embed the full signal trace so future web loaders can show
  score explanations directly.
- Mock baseline traces fall back to `mock://fixtures/signal_events.json` when
  fixture signal events have no event-level source URL.

## ADR-0051: Add Direct Signal Trace Artifact Validation CLI

- Status: accepted
- Date: 2026-05-15

Decision:

Add `python -m src.main --validate-signal-trace path/to/fund_000001_signal_trace.json`.

Rationale:

- Future web loaders and debugging scripts should be able to validate the
  score-provenance artifact without validating or rebuilding a full output
  directory.
- The project already exposes direct validation for other workspace-facing
  artifacts, so signal trace should follow the same operational pattern.

Consequences:

- The CLI reuses the shared signal trace validator.
- Valid artifacts print `Signal trace valid:` with the path.
- Malformed artifacts fail through the standard parser error path.

## ADR-0052: Add Optional Eastmoney Financial Metrics Layer

- Status: accepted
- Date: 2026-05-15

Decision:

Add an optional `--include-financial-metrics` path backed by Eastmoney F10 main
financial indicators.

Rationale:

- Earnings validation should gradually move from fixture and announcement-only
  signals toward real reported financial metrics.
- The Eastmoney F10 endpoint returns no-key revenue and parent-net-profit YoY
  fields that can be normalized without adding pandas, AKShare, or Tushare yet.
- Keeping the layer optional protects default V1 runs from provider instability.

Consequences:

- Raw/scoring artifacts may include `financial_metrics`.
- Provider foundation may include a non-mock `financial_metrics` layer named
  `eastmoney-financial-metrics`.
- Positive revenue/profit YoY metrics derive `revenue_growth_up`; negative
  growth can derive `demand_slowdown`.
- Reviewed-mapping enriched acceptance now exercises this layer and requires
  the resulting financial-derived signal trace.

## ADR-0053: Add Workspace Snapshot Data Layers

- Status: accepted
- Date: 2026-05-15

Decision:

Add a `data_layers` object to `workspace-snapshot-v1`.

Rationale:

- Future web screens need to know which provider payloads are available before
  opening raw/scoring artifacts.
- Source tables describe provider provenance, but they do not summarize payload
  availability or row counts for UI tabs.
- Keeping full payloads in existing artifacts avoids duplicating large raw data
  inside the workspace snapshot.

Consequences:

- Workspace snapshots include `data_layers.version =
  workspace-data-layers-v1`, fund/date identity, and per-layer summaries.
- Each layer records provider name, data quality, mock flag, source URL,
  artifact owner, item count, and availability.
- The validator rejects identity drift, duplicate layer names, invalid
  data-quality values, invalid artifact names, and missing mock/source
  disclosure fields.

## ADR-0054: Render Financial Metrics In Reports

- Status: accepted
- Date: 2026-05-15

Decision:

Render optional `financial_metrics` payloads in Markdown and HTML reports.

Rationale:

- Eastmoney financial metrics now feed deterministic earnings signals, so users
  should be able to inspect the underlying revenue/profit growth rows without
  opening raw JSON.
- Provider/source disclosure remains necessary because the metrics can come
  from optional live providers and may degrade independently from other layers.
- Keeping this as a presentation-only section avoids changing scoring behavior.

Consequences:

- Reports include a `Financial Metrics` table when the payload exists.
- Rows include stock, report period, revenue YoY, parent-net-profit YoY,
  provider, and source URL.
- Reviewed-mapping enriched acceptance now requires `Financial Metrics` in both
  Markdown and HTML reports.

## ADR-0055: Render Valuation Snapshots In Reports

- Status: accepted
- Date: 2026-05-15

Decision:

Render optional `valuation_snapshots` payloads in Markdown and HTML reports.

Rationale:

- Eastmoney valuation snapshots now feed deterministic valuation-risk signals,
  so users need the PE/PB/pressure rows visible in the report.
- The valuation layer is still a snapshot context, not a full historical
  valuation model, so provider basis and source URL must remain visible.
- This is a presentation-only change and does not alter scoring.

Consequences:

- Reports include a `Valuation Snapshots` table when the payload exists.
- Rows include stock, valuation basis, latest price, price change, PE TTM, PB,
  valuation pressure, provider, and source URL.
- Reviewed-mapping enriched acceptance now requires `Valuation Snapshots` in
  both Markdown and HTML reports.

## ADR-0056: Require Data Layer Mock Disclosure In V1 Acceptance

- Status: accepted
- Date: 2026-05-15

Decision:

Make `scripts/validate_v1_acceptance.py` explicitly validate workspace snapshot
`data_layers` mock disclosure.

Rationale:

- Generic workspace snapshot validation checks schema, but V1 acceptance should
  also prove that mock baseline web-loader data cannot be mistaken for live data.
- Future web data tabs will likely read `data_layers` before opening raw
  artifacts, so the summary layer needs the same mock-source guarantee as source
  tables and reports.

Consequences:

- V1 acceptance requires `data_layers.version = workspace-data-layers-v1`.
- V1 acceptance requires at least one mock data-layer row with a
  `mock://fixtures/` source URL.
- A mutated workspace snapshot that rewrites mock data-layer URLs to real-looking
  URLs fails acceptance.

## ADR-0057: Require Reviewed Data Layers In Enriched Acceptance

- Status: accepted
- Date: 2026-05-15

Decision:

Make reviewed-mapping enriched acceptance validate workspace snapshot
`data_layers`.

Rationale:

- The enriched path is the current strongest no-mock-core server flow, so it
  should also cover the future web loader summary, not only raw/scoring/report
  artifacts.
- Future web screens need layer availability before drill-down; missing
  `financial_metrics` or `valuation_snapshots` data-layer rows would hide live
  payloads even when raw JSON contains them.

Consequences:

- Reviewed-mapping enriched acceptance requires `workspace-data-layers-v1`.
- Required data layers are `holdings`, `valuation_snapshots`,
  `financial_metrics`, `news_evidence`, and `derived_signal_events`.
- Required rows must be non-mock, have positive item counts, and disclose source
  URLs.

## ADR-0058: Render Market Quotes In Reports

- Status: accepted
- Date: 2026-05-15

Decision:

Render optional `market_quotes` payloads in Markdown and HTML reports.

Rationale:

- Market quotes can derive momentum and capital-flow signals, so users should
  see the quote rows behind those signals without opening raw JSON.
- Provider/source disclosure remains required because quote data can be live,
  fallback, or unavailable independently from other layers.
- This remains a presentation-only change.

Consequences:

- Reports include a `Market Quotes` table when the payload exists.
- Rows include stock, latest price, change percent, change amount, previous
  close, volume, provider, and source URL.

## ADR-0059: Render News Evidence In Reports

- Status: accepted
- Date: 2026-05-15

Decision:

Render optional `news_evidence` payloads in Markdown and HTML reports.

Rationale:

- News-derived signals are based on RSS title/snippet evidence, so users need
  to inspect the evidence rows and query coverage without opening raw JSON.
- The title/snippet limitation is material and should be visible beside the
  evidence table.
- This is presentation-only and does not change classification or scoring.

Consequences:

- Reports include a `News Evidence` table when the payload exists.
- Rows include title, narrative ID, sentiment, confidence, event date, provider,
  source URL, and classification reason.
- Reports show query coverage and explicitly state that article bodies are not
  parsed in V1.
- Reviewed-mapping enriched acceptance now requires `News Evidence` in both
  Markdown and HTML reports.

## ADR-0060: Render Announcements And Announcement Evidence In Reports

- Status: accepted
- Date: 2026-05-15

Decision:

Render optional `announcements` and `announcement_evidence` payloads in Markdown
and HTML reports.

Rationale:

- Announcement-derived signals should be explainable from the report without
  opening raw JSON.
- V1 classifies announcement metadata only, so the PDF-not-parsed limitation
  must be visible beside the generated evidence.
- The scoring payload should carry `announcements` alongside
  `announcement_evidence` for report rendering and future web loading.

Consequences:

- Reports include `Announcements` and `Announcement Evidence` tables when the
  payloads exist.
- Rows include stock/title/category/date metadata, narrative IDs, confidence,
  generated summaries, provider names, and source URLs.
- Scoring JSON now preserves the original `announcements` payload when
  announcement evidence is enabled.
- Reviewed-mapping enriched acceptance now requires `Announcement Evidence` in
  both Markdown and HTML reports.

## ADR-0061: Validate Announcement Payloads In Workspace Snapshots

- Status: accepted
- Date: 2026-05-15

Decision:

Reject workspace snapshot builds when raw and scoring artifacts disagree on
`announcements` or `announcement_evidence` payloads.

Rationale:

- Future web workspaces should load one coherent server-produced bundle rather
  than choosing between conflicting raw and scoring copies.
- Announcement payloads are duplicated for report rendering and workspace
  loading, so drift can otherwise hide until UI approval screens consume them.
- This keeps the current implementation server-side while preparing for later
  visual approval flows.

Consequences:

- Workspace snapshot building now fails fast on mismatched `announcements`.
- Workspace snapshot building now fails fast on mismatched
  `announcement_evidence`.
- Basic collection shape is checked for both payloads before the snapshot is
  written.

## ADR-0062: Require Optional Provider Layers In Reviewed Workspace Acceptance

- Status: accepted
- Date: 2026-05-15

Decision:

Reviewed-mapping enriched acceptance must require workspace `data_layers` for
`announcements`, `announcement_evidence`, and `market_quotes` in addition to
the previously required holdings, valuation, financial, news, and derived
signal layers.

Rationale:

- The reviewed enriched scenario intentionally enables CNINFO announcements and
  market quotes, so future web data tabs should be able to discover those rows
  from the snapshot without opening raw JSON first.
- Reports now show these optional payloads; workspace acceptance should enforce
  the same source visibility for the later UI.
- Missing optional data-layer rows are contract gaps even when the raw/scoring
  payloads exist.

Consequences:

- Reviewed-mapping enriched acceptance fails if `announcements`,
  `announcement_evidence`, or `market_quotes` data-layer rows are missing.
- These layers must be non-mock, have rows, and disclose source URLs.

## ADR-0063: Validate Announcement Provider Contracts

- Status: accepted
- Date: 2026-05-15

Decision:

Add reusable validators for announcement provider payloads and generated
announcement evidence payloads, and call them from CNINFO orchestration.

Rationale:

- Malformed real-provider payloads should fail fast instead of being silently
  converted into empty evidence.
- Announcement evidence is now used by scoring, reports, and future workspace
  loading, so it needs the same contract discipline as news, valuation, and
  financial provider payloads.
- The converter should still track malformed individual announcement rows, but
  top-level payload shape errors are provider contract failures.

Consequences:

- CNINFO provider output is validated before it is returned.
- Optional announcement orchestration validates the provider payload before
  conversion.
- Generated announcement evidence is validated before leaving the converter.

## ADR-0064: Validate Optional Provider Payloads At Orchestration Boundaries

- Status: accepted
- Date: 2026-05-15

Decision:

Validate market quote, valuation snapshot, financial metrics, and news evidence
payloads inside orchestration immediately after optional providers return.

Rationale:

- Built-in providers validate their own payloads, but injected test providers
  and future adapters should not be able to bypass provider contracts.
- Malformed optional payloads can otherwise fail later as generic type errors
  or silently produce empty derived signals.
- Boundary validation keeps failure messages tied to the provider contract.

Consequences:

- Optional market quote runs fail fast on malformed market payloads.
- Optional valuation and financial metric runs fail fast on malformed provider
  payloads.
- Optional news evidence runs fail with `ProviderContractError` before derived
  signal generation sees malformed evidence rows.

## ADR-0065: Validate Optional Payloads In Artifact Contract Checks

- Status: accepted
- Date: 2026-05-15

Decision:

When `_validate_artifact_contracts` reads manifest-referenced raw and scoring
JSON, validate all optional provider payloads present in those artifacts.

Rationale:

- Future web loaders and audits may validate existing outputs without rerunning
  the pipeline.
- Runtime provider-boundary validation is not enough for edited, archived, or
  externally generated artifact directories.
- Optional payload contracts should be enforced consistently across runtime and
  offline validation.

Consequences:

- Offline artifact validation now checks `announcements`,
  `announcement_evidence`, `market_quotes`, `valuation_snapshots`,
  `financial_metrics`, and `news_evidence` when present.
- Malformed optional payloads in either raw or scoring artifacts fail before
  workspace snapshots are built.
