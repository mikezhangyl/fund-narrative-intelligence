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
- In-place registry overwrite requires `--allow-registry-overwrite`.
- Normal report generation never calls review-action persistence.
