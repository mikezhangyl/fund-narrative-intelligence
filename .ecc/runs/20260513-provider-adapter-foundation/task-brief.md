# Task Brief

## Goal

Prepare the V1 provider layer for real fund holding data while preserving deterministic mock fallback.

## Scope

- Research and document a no-key public fund-holding source candidate.
- Add a provider protocol/interface.
- Add a real-provider adapter for fund holdings only if the source can be cleanly normalized.
- Preserve registry, mappings, evidence, and signal services as local V1 fixtures.
- Add tests for provider selection, normalization, and fallback behavior.

## Out Of Scope

- Full real market data ingestion.
- Real evidence/news/financial/valuation providers.
- API-key providers.
- LLM mapping.
- Frontend workspace.

## Required Verification

- Full pytest suite.
- Acceptance command for `000001`.
- Batch fixture command.
- Real provider mode fallback or successful real holdings normalization with contract validation.
