# R9 Workspace Import Export

## Scope

Implement local workspace import/export:

- `MIK-179` Workspace import and export package.
- `MIK-182` Workspace import/export manifest contract.

## Acceptance

- Export package includes workspace state, saved views, preferences, and non-sensitive artifact index rows.
- Export manifest declares schema version, compatibility, contents, excluded sensitive paths, and restore policy.
- Import restores only local workspace state and does not overwrite trusted service records.
- JSON package and canonical Chinese HTML summary are generated.

## Verification

- TDD tests for export sanitization, deterministic import, CLI export/import, and Chinese HTML.
- Full test suite, lint, diff whitespace, and ECC validation.
