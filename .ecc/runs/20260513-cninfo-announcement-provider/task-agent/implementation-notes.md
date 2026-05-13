# Implementation Notes

## Summary

Added an optional CNINFO announcement provider adapter foundation.

## Changes

- Added `src/providers/cninfo.py`.
- Added CNINFO announcement query payload construction.
- Added stock-code based CNINFO market-column selection for SZSE, SSE, and Beijing exchange codes.
- Added response normalization into the V1 announcement-provider contract.
- Added injectable fetcher support for deterministic tests.
- Added controlled unavailable payloads and `provider_unavailable` events for fetch failures.
- Added invalid stock-code handling that records degradation without calling CNINFO.
- Documented that the provider is optional and not part of the default report pipeline.

## Result

The project now has a first real non-holdings intelligence-source adapter foundation without introducing external endpoint instability into normal report generation.
