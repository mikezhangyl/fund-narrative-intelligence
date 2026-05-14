# Mock Data Source URL Disclosure Execution Plan

## Goal

Make mock-backed outputs visibly self-identifying in source URL fields, not only in prose notices, so future web UI surfaces cannot accidentally present mock data as live data.

## Scope

- Add stable `mock://fixtures/...` source identifiers for mock fund holdings and fixture-backed provider layers.
- Preserve existing data-quality and confidence downgrade behavior.
- Cover raw/scoring/report output with tests.
- Update project memory.

## Non-Goals

- No real provider changes.
- No fixture schema migration.
- No web UI work.

## Acceptance

- Mock raw/scoring JSON contains mock source identifiers.
- Markdown/HTML source tables render mock source identifiers.
- Full lint, compile, coverage, and smoke checks pass.
