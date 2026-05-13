# Implementation Notes

## Summary

Added an explicit `eastmoney` provider mode for no-key Eastmoney/Tiantian Fund holdings while preserving mock as the deterministic baseline.

## Source Research

- efinance documents `FundMNInverstPosition` as the Eastmoney mobile fund-holdings endpoint.
- AKShare documents CNINFO as another broader fund report source, but it is not single-fund top-holdings first. Eastmoney is a better V1 fit for `fund_code -> holdings`.

## Changes

- Added `DataProvider` protocol.
- Added `EastmoneyFundHoldingProvider`.
- Added Eastmoney response normalization.
- Added fallback from Eastmoney to mock when fetch or normalization fails.
- Added `eastmoney` CLI provider mode.
- Added Premium Baijiu Consumption fixture mappings so `161725` can produce a narrative report with real holdings.
- Hardened report generation when holdings have no mapping.

## Smoke Result

`python -m src.main --fund-code 161725 --provider-mode eastmoney` generated all four artifacts. Primary narrative: `Premium Baijiu Consumption`; stage: `diverging`; no fallback event.
