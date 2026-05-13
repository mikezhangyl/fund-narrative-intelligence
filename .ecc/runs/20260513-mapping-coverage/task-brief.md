# Task Brief

## Goal

Add mapping coverage metadata and rule-based fallback mappings for holdings that lack exact stock-code mappings.

## Scope

- Compute covered/uncovered holdings and weight coverage.
- Generate low-confidence fallback mappings from narrative registry aliases/related terms and holding industry/name text.
- Expose mapping coverage in raw/scoring JSON and Markdown/HTML reports.
- Preserve exact mapping behavior for existing fixtures.

## Out Of Scope

- LLM mapping.
- Automatic registry mutation.
- Scoring formula changes.
- Real provider expansion beyond existing Eastmoney holdings.

## Required Verification

- Full pytest suite.
- Original acceptance command.
- Batch fixtures.
- Eastmoney smoke report.
