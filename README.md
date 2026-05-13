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

The smoke command writes:

```text
outputs/real_fund_smoke_summary.json
outputs/real_fund_smoke_summary.md
```

The smoke summary is per-fund isolated: if one live provider call fails, the summary still records that fund as `failed`, keeps the remaining fund checks running, and exits non-zero when any fund fails or misses the coverage threshold.

When real holdings are not fully mapped, the summary JSON includes `unmapped_holdings` with stock code, stock name, industry, and weight. The Markdown summary also adds a `Mapping Gaps` section so registry expansion can be driven by concrete live-holding gaps.

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

Reports include a `Data Source Notice` whenever the run uses mock data, degraded provider fallback, or mixed real/mock layers. This notice lists each provider layer and whether it is mock-backed.

Narrative sections include deterministic interpretation notes for lifecycle stage, risk pressure, and confidence. These notes are explanatory only and do not produce allocation or trading recommendations.

## Product Docs

- [Product thesis](docs/product/fund-narrative-intelligence-system.html)
- [V1 implementation spec](docs/product/v1-implementation-spec.md)
