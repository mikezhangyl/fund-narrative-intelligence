# Implementation Notes

## Summary

Added mapping coverage metadata and registry-term fallback mapping.

## Changes

- Added `build_mapping_result`.
- Exact stock-code mappings remain preferred.
- Holdings without exact mappings can map via narrative aliases/related terms matched against stock name and industry.
- Raw/scoring JSON now include `mapping_coverage` and `unmapped_holdings`.
- Markdown/HTML reports display mapping coverage and methods.

## Smoke Result

Eastmoney `161725` produced `Premium Baijiu Consumption / diverging` with coverage ratio `1.0` and mapping methods `fixture_rule: 8`, `registry_term_rule: 2`.
