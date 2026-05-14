# Fund Narrative Intelligence

Fund Narrative Intelligence is a report-first system for analyzing what market narratives a fund is exposed to through its holdings, then evaluating those narratives with evidence and signal-backed scoring.

V1 is mock-provider first. It does not require real API credentials and does not produce investment advice or buy/sell signals.

## Quick Start

List available mock fixtures:

```bash
python -m src.main --list-fixtures
```

Run the V1 acceptance command:

```bash
python -m src.main --fund-code 000001
```

Run all mock fixtures:

```bash
python -m src.main --run-all-fixtures
```

Run the live Eastmoney smoke set:

```bash
python -m src.main --run-real-smoke
```

Run the live Eastmoney + CNINFO announcement evidence smoke:

```bash
python -m src.main --run-announcement-smoke
```

Inspect provider layers without generating report artifacts:

```bash
python -m src.main --fund-code 000001 --provider-diagnostics
```

Optionally include CNINFO announcement metadata as evidence:

```bash
python -m src.main --fund-code 000001 --include-cninfo-announcements --announcement-start-date 2026-05-01
```

Generated artifacts:

```text
outputs/fund_000001_raw.json
outputs/fund_000001_scoring.json
outputs/fund_000001_report.md
outputs/fund_000001_report.html
```

Run tests:

```bash
python -m pytest -q
```

Install development tooling:

```bash
python -m pip install -e ".[dev]"
```

Run quality gates:

```bash
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m compileall -q src tests scripts
```

## Current Scope

- Python CLI.
- Local mock providers and JSON fixtures.
- Mock intelligence layer providers for registry, mappings, evidence, signals, and reserved market/valuation/announcement/news interfaces.
- Optional CNINFO announcement provider adapter with injectable fetcher; it is not part of the default report pipeline yet.
- Optional announcement-to-evidence conversion layer; it classifies announcement metadata into V1 evidence records without parsing PDFs.
- Optional CNINFO announcement evidence orchestration behind `--include-cninfo-announcements`; default runs do not call CNINFO.
- Narrative registry loading.
- Stock-to-narrative mapping.
- Fund narrative aggregation.
- Mapping coverage and registry-term fallback mapping for unmapped holdings.
- Signal decay and five-dimension scoring.
- Markdown report generation and structured HTML report generation.
- Controlled errors for missing fixtures or invalid provider payloads.

## Mock Scenario Fixtures

| Fund Code | Scenario | Expected Primary Narrative | Expected Stage |
| --- | --- | --- | --- |
| `000001` | AI infrastructure validation | AI Infrastructure | `strengthening` |
| `000002` | AI power crowding | AI Power Demand | `crowded` |
| `000003` | EV pressure and counter evidence | EV Price War | `dead` |

## Provider Modes

`mock` is the default provider mode.

```bash
python -m src.main --fund-code 000001 --provider-mode mock
```

`real` is accepted for interface testing, but V1 deliberately degrades to mock and records a `provider_fallback` event because real providers are not implemented yet.

```bash
python -m src.main --fund-code 000001 --provider-mode real
```

`eastmoney` tries the no-key Eastmoney/Tiantian Fund mobile holdings endpoint for fund holdings. Registry, stock narrative mapping, evidence, and signal fixtures still come from local V1 data.

```bash
python -m src.main --fund-code 161725 --provider-mode eastmoney
```

If the Eastmoney request fails, the provider records a `provider_fallback` event and falls back to local mock fixtures when a matching fixture exists.

Reports always disclose mock or degraded data in a `Data Source Notice` section. A pure mock run is marked as `mock`; an Eastmoney holdings run with fixture-backed registry, mappings, evidence, and signals is marked as `partial` so users do not mistake it for a fully real environment.

When `--include-cninfo-announcements` is enabled, reports add an `Announcements` provider layer and generated evidence summaries state that V1 classified announcement metadata only; source PDFs are not parsed.

For CNINFO announcement search, V1 sends Shanghai and Shenzhen stock selectors in `code,orgId` form, such as `600519,gssh0600519` and `000001,gssz0000001`. This is covered by unit tests and by the live announcement smoke command.

## Real Provider Status

The first real provider adapter is `eastmoney`, covering fund holdings only. It normalizes Eastmoney fields such as stock code, stock name, holding percentage, holding change, industry, and public holding date into the same V1 fund-holdings contract used by mock providers.

## Real Fund Smoke Set

| Fund Code | Scenario | Expected Primary Narrative | Calibrated Stage |
| --- | --- | --- | --- |
| `161725` | Baijiu consumption | Premium Baijiu Consumption | `diverging` |
| `320007` | Semiconductor | Semiconductor Capex Cycle | `strengthening` |
| `003096` | Healthcare | Healthcare Innovation | `diverging` |
| `003834` | New energy | New Energy Equipment | `weakening` |
| `001475` | Defense | Defense Aerospace | `strengthening` |
| `000991` | Real estate chain | Real Estate Stabilization | `weakening` |

The current calibrated smoke baseline passes the coverage threshold for all six funds while keeping the stage distribution above. Some holdings are intentionally unmapped when a known-bad fallback candidate is excluded.

The smoke command writes:

```text
outputs/real_fund_smoke_summary.json
outputs/real_fund_smoke_summary.md
```

The smoke summary is per-fund isolated: if one live provider call fails, the summary still records that fund as `failed`, keeps the remaining fund checks running, and exits non-zero when any fund fails or misses the coverage threshold.

When real holdings are not fully mapped, the summary JSON includes `unmapped_holdings` with stock code, stock name, industry, and weight. The Markdown summary also adds a `Mapping Gaps` section so registry expansion can be driven by concrete live-holding gaps.

The summary also reports `multi_mapped_holdings` when one holding maps to multiple narratives. This is intentional diagnostic output: full coverage should not hide possible over-broad registry terms or genuinely cross-domain companies.

The summary also aggregates `mapping_precision_flags` into a `Mapping Precision Flags` section so curation work items from the fixed real-smoke set are visible without opening every fund report.

The `--run-real-smoke` terminal output includes `precision_flags=<count>`, `excluded_candidates=<count>`, `candidate_narratives=<count>`, and `review_queue=<count>` for each fund so CI logs and quick local runs show whether coverage is clean or still has mapping precision, exclusion, or taxonomy review work.

Known-bad fallback candidates can be listed in `mapping_exclusions.json`. These candidates are not used for scoring or aggregation; instead, raw/scoring JSON, reports, and real-smoke summaries show them as `Excluded Mapping Candidates` with the review reason.

Review-only candidate narratives live in the registry's `candidate_narratives` list. They are shown in raw/scoring JSON, reports, and real-smoke summaries when related exclusions appear, but they are not part of active stock mapping, aggregation, or scoring until human review promotes them into the active registry.

Candidate promotion is an explicit review action. The backend supports approve/reject/defer state transitions for a future web review workspace, but the report pipeline never promotes candidates automatically.

Raw/scoring JSON also includes a `candidate_review_queue` object. This is a read-ready queue for a future web workspace: each item links a candidate narrative to related exclusions, exposes available actions, and includes an approval action template. It does not persist actions or change scoring by itself.

The pipeline also writes `outputs/fund_<code>_review_queue.json` as a dedicated future-workspace artifact so a web review surface can load candidate review work without parsing the full raw or scoring snapshots.

When a fallback registry-term match maps one holding to multiple narratives, V1 keeps all mappings but lowers their confidence from `0.52` to `0.42`, marks each mapping with `needs_review`, and writes `mapping_precision_flags` into raw/scoring JSON plus the Markdown/HTML report.

When a fallback mapping is supported only by a broad industry term, V1 keeps the mapping but lowers confidence from `0.52` to `0.48`, marks it with `broad_industry_fallback`, and recommends `curation_review`. This catches cases such as a generic `电子` industry match before it is treated like a more specific stock-name or product-term match.

Every selected stock-to-narrative mapping also emits a `mapping_rationales` row in raw/scoring JSON and reports. This row explains the mapping method, narrative name, confidence, matched registry terms when available, and whether the mapping needs manual review. For V1 this makes the answer to "why is this stock in this narrative?" explicit instead of implicit in fixtures or broad industry rules.

The latest registry curation pass replaced clear broad industry-only matches with company-level terms for baijiu, healthcare, defense, new energy, real estate chain, and selected semiconductor equipment/EDA holdings. The remaining ambiguous semiconductor candidates are explicitly excluded and left for narrative reassessment rather than forced into the current registry.

## Announcement Evidence Smoke

The announcement smoke command validates the optional real announcement path against an A-share fund example:

```bash
python -m src.main --run-announcement-smoke
```

It writes:

```text
outputs/announcement_evidence_smoke_summary.json
outputs/announcement_evidence_smoke_summary.md
```

The smoke checks that CNINFO announcements are returned, converted into evidence, represented as a non-mock `Announcements` provider layer, and paired with a visible data-source notice so mixed real/mock output is not mistaken for a fully real environment.

## Report Output

Each run writes both Markdown and HTML. The HTML report is rendered from structured scoring data with headings, sections, holdings tables, narrative dimension tables, evidence lists, and a disclaimer.

Reports also include mapping coverage so real-provider runs make clear how much of a fund's holdings are explained by current registry and mapping fixtures.

Reports include `Mapping Rationales` so users can inspect why each mapped holding was assigned to a narrative. Fixture mappings are labeled as explicit fixture rules; fallback mappings list the registry terms that matched stock code, stock name, or industry.

Reports include a `Data Source Notice` whenever the run uses mock data, degraded provider fallback, or mixed real/mock layers. This notice lists each provider layer and whether it is mock-backed.

Narrative sections include deterministic interpretation notes for lifecycle stage, risk pressure, and confidence. These notes are explanatory only and do not produce allocation or trading recommendations.

## Product Docs

- [Product thesis](docs/product/fund-narrative-intelligence-system.html)
- [V1 implementation spec](docs/product/v1-implementation-spec.md)
