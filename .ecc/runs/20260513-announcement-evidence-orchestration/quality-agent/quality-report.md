# Quality Report

## Status

Passed.

## Checks

- CLI/orchestration tests failed first, then passed after implementation.
- Focused and full lint/test/coverage/compile checks pass.
- Existing live Eastmoney smoke still passes.
- Mock-fund opt-in path displays `Announcements` as unavailable with invalid stock-code degradation.
- Eastmoney A-share opt-in path displays fresh Eastmoney holdings and fresh CNINFO announcement layer.

## Residual Risks

- CNINFO endpoint behavior may change.
- Announcement evidence remains metadata-only.
- The current scoring path still depends on fixture-backed signal events.
