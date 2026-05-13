# Implementation Notes

## Summary

Added optional announcement-to-evidence conversion for CNINFO-style announcement metadata.

## Changes

- Added `src/modules/evidence/announcements.py`.
- Added deterministic title/category classification for risk, earnings, orders, capital support, financial reports, governance, and generic announcements.
- Added stock-code-to-narrative mapping through existing stock mapping records.
- Added confidence calculation from classification confidence, mapping confidence, and provider data quality.
- Added skipped/unmapped accounting without raising uncontrolled errors.
- Kept conversion optional and outside the default report pipeline.

## Result

The project now has a stable boundary from real announcement metadata to V1 evidence records while preserving mock-first report behavior.
