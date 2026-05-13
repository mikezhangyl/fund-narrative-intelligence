# CNINFO Announcement Provider Execution Plan

## Purpose

Add the first optional real intelligence-source adapter foundation for structured announcements.

## Scope

- Add `CNInfoAnnouncementProvider`.
- Add request payload builder and response normalizer.
- Select CNINFO market column from stock-code prefixes.
- Support injectable fetcher for deterministic tests.
- Return controlled `unavailable` payloads when provider fetch fails.
- Treat invalid stock codes as degradation without calling the provider.
- Keep the default V1 report pipeline unchanged.

## Acceptance

- Unit tests cover payload construction, market-column selection, response normalization, injected fetch success, invalid stock codes, and fetch failure.
- Existing report pipeline tests remain green.
- Full quality gates pass.

## Status

Implemented, verified, and ready to merge.

## Run Record

- `.ecc/runs/20260513-cninfo-announcement-provider/`
