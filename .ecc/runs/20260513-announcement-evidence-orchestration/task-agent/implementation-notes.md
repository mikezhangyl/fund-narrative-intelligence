# Implementation Notes

## Summary

Added explicit optional orchestration for CNINFO announcement evidence.

## Changes

- Added `--include-cninfo-announcements` and `--announcement-start-date` CLI options.
- Added optional announcement provider injection to `run_pipeline`.
- Wired CNINFO announcement metadata through `convert_announcements_to_evidence`.
- Added raw/scoring `announcements` and `announcement_evidence` payloads only when opted in.
- Extended provider foundation to support extra layers, including `Announcements`.
- Updated `AnnouncementProvider` protocol to accept `start_date`.
- Kept default report generation unchanged.

## Result

Users can explicitly request CNINFO announcement metadata as evidence, and reports disclose whether the announcement layer is fresh, unavailable, mock-backed, or degraded.
