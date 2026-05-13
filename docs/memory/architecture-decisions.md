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
