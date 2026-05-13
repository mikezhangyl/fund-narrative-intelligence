# CNINFO OrgId Announcement Smoke Execution Plan

## Goal

Validate the optional CNINFO announcement evidence path against a real A-share fund example and make the check repeatable.

## Scope

- Fix CNINFO Shanghai/Shenzhen announcement query selectors to use `code,orgId` form.
- Add a live announcement-evidence smoke command for the `161725` Eastmoney + CNINFO path.
- Verify the smoke fails if announcement metadata or converted evidence is empty.
- Verify mixed real/mock output still carries a visible data-source notice.

## Non-Goals

- Making CNINFO announcements default-on.
- Parsing announcement PDFs.
- Replacing fixture-backed registry, mapping, evidence, or signal layers.
- Expanding the full six-fund Eastmoney smoke set.

## Acceptance Checks

- `pytest tests/test_cninfo_provider.py tests/test_announcement_smoke.py -q`
- `python -m src.main --run-announcement-smoke`
- Standard lint, coverage, and compile gates pass.

## Run Directory

- `.ecc/runs/20260513-cninfo-orgid-announcement-smoke/`
