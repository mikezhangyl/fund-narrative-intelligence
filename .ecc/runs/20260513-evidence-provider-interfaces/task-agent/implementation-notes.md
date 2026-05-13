# Implementation Notes

## Summary

Added explicit provider-layer interfaces and mock implementations for V1 intelligence sources.

## Changes

- Added `src/providers/intelligence.py`.
- Added mock providers for narrative registry, stock mappings, evidence, and signal events.
- Added reserved mock providers for market data, valuation, announcements, and news evidence.
- Rewired `MockDataProvider` to compose `MockIntelligenceProviderSet`.
- Preserved provider foundation provenance so fixture-backed intelligence layers remain visible in reports.
- Added tests for provider contracts, deep-copy behavior, provenance, and empty reserved mock payloads.
- Updated README, V1 spec, project memory, and ADRs.

## Result

Future real intelligence sources can plug into layer provider contracts without rewriting the orchestrator or pretending unimplemented providers return real data.
