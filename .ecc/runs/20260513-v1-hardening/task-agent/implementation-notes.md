# Implementation Notes

## Summary

Hardened the V1 mock pipeline with provider contract validation and clearer CLI behavior.

## Changes

- Added controlled pipeline exceptions in `src/errors.py`.
- Added provider payload validation in `src/validation.py`.
- Updated `MockDataProvider` to validate loaded fixtures before returning data.
- Added `MockDataProvider.list_fund_codes()`.
- Added CLI `--list-fixtures`.
- Converted missing fund fixture failures into controlled stderr errors.
- Added README usage docs and updated product/memory docs.

## Rationale

Before adding real data providers, the local provider contract needs to be stable. Real providers can now be adapted to the same expected payload shapes and receive early validation failures.
