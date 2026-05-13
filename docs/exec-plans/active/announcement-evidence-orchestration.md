# Announcement Evidence Orchestration Execution Plan

## Purpose

Expose an explicit optional orchestration path that can fetch CNINFO announcement metadata, convert it into V1 evidence records, and disclose the announcement provider layer in reports.

## Scope

- Add a CLI flag for optional CNINFO announcement evidence.
- Keep default report generation unchanged.
- Inject generated announcement evidence into raw/scoring payloads only when the option is enabled.
- Add an `announcements` provider-foundation layer when the option is enabled.
- Preserve controlled degradation when CNINFO is unavailable or stock codes are not accepted by the provider.

## Out Of Scope

- Default-on CNINFO usage.
- PDF download or parsing.
- Signal generation from announcement evidence.
- Historical replay or alerting.

## Acceptance

- Default `python -m src.main --fund-code 000001` remains mock-backed and discloses mock data.
- Optional announcement path writes `announcements`, `announcement_evidence`, and an `Announcements` layer in provider foundation.
- CLI passes `--include-cninfo-announcements` and `--announcement-start-date` into orchestration.
- Full quality gates pass.

## Status

Implemented, verified, and ready to merge.

## Run Record

- `.ecc/runs/20260513-announcement-evidence-orchestration/`
