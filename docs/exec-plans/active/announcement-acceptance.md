# Announcement Acceptance

## Goal

Add a strict manual acceptance path for the first partially real evidence flow:
Eastmoney fund holdings plus CNINFO announcement metadata converted into V1
evidence.

## Scope

- Run fund `161725` through `--provider-mode eastmoney`.
- Enable `--include-cninfo-announcements` with start date `2026-01-01`.
- Validate generated artifact contracts.
- Fail if live holdings, CNINFO announcements, or CNINFO evidence are missing.
- Keep registry, stock mapping, base evidence, and signal fixtures explicit.

## Non-Goals

- Do not make CNINFO the default report behavior yet.
- Do not parse announcement PDFs.
- Do not add this live-provider check to CI.

## Acceptance

```bash
python scripts/validate_announcement_acceptance.py --output-dir outputs/announcement_161725
```

Expected result:

- Holdings layer is fresh Eastmoney data.
- Announcements layer is non-mock CNINFO data.
- Raw and scoring artifacts contain CNINFO-derived announcement evidence.
- Fixture-backed intelligence layers remain marked with `mock://fixtures/...`.
- Markdown and HTML reports disclose mixed Eastmoney + CNINFO + Mock fixture
  data.
