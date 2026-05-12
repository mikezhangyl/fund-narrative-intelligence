---
name: qa-evidence-report
description: Use to turn manual or automated QA observations into defect records, evidence indexes, reproduction steps, test reports, and stakeholder-ready summaries.
---

# QA Evidence Report

Use after testing activity produces observations, defects, screenshots, traces, HAR files, or videos.

## Evidence Rules

- Every defect needs reproduction steps, expected result, actual result, severity, environment, and evidence path.
- Keep bulky raw evidence under `.ecc/test-runs/<run-id>/evidence/`.
- Reference ignored raw evidence from `evidence/index.md`.
- Summarize important evidence in committed markdown reports.

## Report Targets

- `.ecc/test-runs/<run-id>/defects.md`
- `.ecc/test-runs/<run-id>/evidence/index.md`
- `.ecc/test-runs/<run-id>/report.md`
- `docs/testing/risk-register.md`

