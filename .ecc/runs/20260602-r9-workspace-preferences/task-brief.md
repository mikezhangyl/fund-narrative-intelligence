# R9 Workspace Preferences

## Scope

Implement local workflow preferences and redaction rules:

- `MIK-178` User preferences and workflow defaults.
- `MIK-181` Preference redaction and validation contract.

## Acceptance

- Users/operators can persist default surface, watchlist, date window, density, theme, and demo/live mode.
- Preference inputs reject invalid option sets.
- Secret-like keys are redacted before persistence and recorded as redaction events.
- Workspace state JSON and canonical Chinese HTML expose preferences without leaking credentials.

## Verification

- TDD tests for preference persistence, validation, CLI behavior, and HTML rendering.
- Full project test suite, lint, diff whitespace, and ECC run validation.
