# Real Smoke Registry Curation Execution Plan

## Purpose

Use `broad_industry_fallback` real-smoke diagnostics to replace clear broad industry-only matches with more specific company-level registry terms.

## Scope

- Extract broad industry-only fallback rows from the fixed real-smoke set.
- Add tests for clear company-level replacements.
- Add company-specific terms for clear mappings across baijiu, healthcare, defense, new energy, real estate chain, and selected semiconductor equipment/EDA holdings.
- Keep ambiguous broad flags visible instead of forcing questionable mappings.

## Non-Goals

- Resolving every broad flag in one pass.
- Adding a new narrative category.
- Removing broad industry terms from the registry.

## Acceptance

- Clear curation candidates no longer emit `broad_industry_fallback`.
- Real smoke still reaches 100% coverage and keeps calibrated stages stable.
- Remaining ambiguous broad flags are documented for follow-up.
- Full quality gates and live smoke commands pass.

## Run Record

- `.ecc/runs/20260514-real-smoke-registry-curation/`
