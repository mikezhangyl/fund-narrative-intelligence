# Architecture Decisions Index

Last updated: 2026-05-26

Use this file as the default ADR entry point. Read `docs/memory/architecture-decisions.md` only when a task needs full rationale, exact consequences, or a specific ADR body.

## Current Decisions To Keep In Working Context

| ADR | Short decision |
| --- | --- |
| ADR-0001 | Use the merged ECC + Superpower + memory framework, but activate it progressively. |
| ADR-0002 | V1 intelligence engine is Python CLI first; frontend workspace is deferred. |
| ADR-0007 | User-facing reports must disclose mock, mixed, fallback, and degraded provider foundations. |
| ADR-0008 | Intelligence sources are separate provider-layer interfaces. |
| ADR-0022 | Preserve future web approval workflow shape in current artifacts. |
| ADR-0027 | Candidate review persistence must be explicit and audit-backed. |
| ADR-0028 | Pipeline manifests are the web-loading discovery surface. |
| ADR-0036 | Registry-rule stock mapping mode is explicit and single-run scoped. |
| ADR-0038 | Provider-derived base intelligence mode is opt-in. |
| ADR-0039 | Reviewed narrative registry is file-backed and explicit. |
| ADR-0040 | Reviewed stock mappings are file-backed and explicit. |
| ADR-0044 | Workspace snapshot is the future web loader contract. |
| ADR-0067 | Resolve security market identity before provider symbol formatting. |
| ADR-0068 | Default news evidence is multi-source but source-disciplined. |
| ADR-0069 | Prefer independent source diversification over wrapper count. |
| ADR-0070 | Default harness context is summary-first to reduce unnecessary token use. |
| ADR-0071 | Formal reader-facing reports use HTML as the canonical readable artifact. |

## Decision Areas

- Framework and process: ADR-0001, ADR-0005, ADR-0070.
- Core engine and acceptance: ADR-0002 through ADR-0006, ADR-0071.
- Provider provenance and source layers: ADR-0007 through ADR-0013, ADR-0029 through ADR-0035, ADR-0045 through ADR-0049, ADR-0052 through ADR-0069.
- Mapping, curation, and candidate review: ADR-0014 through ADR-0027, ADR-0036 through ADR-0042.
- Web-loadable artifacts and future workspace contracts: ADR-0028, ADR-0043, ADR-0044, ADR-0050, ADR-0051, ADR-0053 through ADR-0066.

## Lookup Rule

For routine development, use this index plus `docs/memory/current-brief.md`. For a decision-specific task, open the full ADR file and search by ADR number or title instead of loading the whole file.
