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

## V1 Acceptance Command

`python -m src.main --fund-code 000001`

Expected artifacts:

- `outputs/fund_000001_raw.json`
- `outputs/fund_000001_scoring.json`
- `outputs/fund_000001_review_queue.json`
- `outputs/fund_000001_report.md`
- `outputs/fund_000001_report.html`

## Technical Stack

- V1 engine: Python CLI.
- Runtime dependencies: standard library only for the first mock pipeline.
- Test runner: pytest.
- Development quality tools: pytest, ruff, and coverage are declared in `pyproject.toml` under the `dev` extra.
- Standard setup command: `python -m pip install -e ".[dev]"`.
- Standard quality commands: `python -m ruff check .`, `python -m coverage run -m pytest -q`, `python -m coverage report`, and `python -m compileall -q src tests scripts`.
- Data: local JSON fixtures and mock providers.
- Future UI: Node.js / Next.js can be added later as a separate workspace layer. Candidate narrative review and approval will eventually happen in a web UI, so V1 structured outputs should remain directly renderable and action-ready for a future review workspace.
- CLI fixture discovery: `python -m src.main --list-fixtures`.
- Batch fixture command: `python -m src.main --run-all-fixtures`.
- Live Eastmoney smoke command: `python -m src.main --run-real-smoke`.
- Live Eastmoney + CNINFO announcement smoke command: `python -m src.main --run-announcement-smoke`.
- Provider diagnostics command: `python -m src.main --fund-code 000001 --provider-diagnostics` prints provider foundation JSON without generating report artifacts.
- Optional CNINFO announcement evidence command: `python -m src.main --fund-code 000001 --include-cninfo-announcements --announcement-start-date 2026-05-01`.
- Provider payloads are validated before orchestration proceeds.
- Real holdings adapter: `python -m src.main --fund-code 161725 --provider-mode eastmoney` tries Eastmoney/Tiantian Fund fund holdings and keeps local fixtures for all other V1 intelligence layers.
- Provider foundation metadata separates holdings, narrative registry, stock mappings, evidence, and signals so mixed real/mock runs are marked `partial` instead of `fresh`.
- Mock intelligence layer providers now expose separate interfaces for registry, stock mappings, evidence, signals, and reserved market/valuation/announcement/news sources.
- Optional `CNInfoAnnouncementProvider` exists as the first real intelligence-source adapter foundation; it is not wired into the default report pipeline.
- Optional announcement-to-evidence conversion and orchestration exist for CNINFO-style announcement metadata; default reports do not call CNINFO unless `--include-cninfo-announcements` is set.
- CNINFO announcement search for Shanghai and Shenzhen A-shares must send `stock` as `code,orgId`, for example `600519,gssh0600519` or `000001,gssz0000001`; using only the 6-digit code can return empty results.
- Markdown and HTML reports include a `Data Source Notice` whenever a run uses mock data, fallback/degradation, or mixed real/mock layers.
- HTML reports render semantic sections/tables directly from structured scoring data.
- Mapping output includes coverage ratio, mapping method counts, and unmapped holdings.
- Unmapped holdings can receive low-confidence `registry_term_rule` mappings from narrative registry aliases/related terms matched against stock name and industry.
- Multi-match `registry_term_rule` mappings are retained but lowered from confidence `0.52` to `0.42`, marked `needs_review`, and emitted as `mapping_precision_flags`.
- Single fallback mappings supported only by broad holding industry terms are lowered from confidence `0.52` to `0.48`, marked `broad_industry_fallback`, and emitted with `curation_review`.
- Selected stock-to-narrative mappings also emit `mapping_rationales` in raw/scoring JSON and reports, including method, confidence, matched registry terms, and review flags so users can see why a holding was mapped to a narrative.
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
- `python -m src.main --preview-review-action path/to/action.json` writes a review-action preview artifact without requiring `--fund-code` and without mutating `data/fixtures/narrative_registry.json`.
- Review-action preview artifacts include `registry_delta` so future web approval screens can show added active narratives and candidate state transitions without diffing the full registry.
- Review-action preview artifacts are validated before write; the reusable validator checks preview metadata, summary, registry delta, and result registry shape.
- `python -m src.main --persist-review-action path/to/action.json --registry-output path/to/registry.next.json` writes an explicitly reviewed registry result without requiring `--fund-code`; in-place overwrite requires `--allow-registry-overwrite`, and overwriting an existing non-source output requires `--allow-registry-output-overwrite`.
- Review-action persistence writes a separate `candidate_review_action_<action_id>_persistence.json` audit artifact under `--output-dir` by default, or to `--persistence-result-output` when provided.
- Review-action persistence requires an audit output path or directory even for direct API callers; registry and audit writes are rollback-protected so audit write failure does not leave a new registry output behind.
- `python -m src.main --run-real-smoke` prints `precision_flags=<count>`, `excluded_candidates=<count>`, `candidate_narratives=<count>`, and `review_queue=<count>` per fund in stdout.
- Announcement-evidence smoke summaries check real CNINFO metadata count, converted evidence count, the non-mock `Announcements` layer, and visible mixed/mock data-source disclosure.

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

## Open Questions

- Should the next iteration broaden the narrative registry and rules for more Eastmoney real-fund sectors, or improve the scoring language and report interpretation?
