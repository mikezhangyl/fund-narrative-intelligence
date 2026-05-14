# Review Action Preview

## Goal

Add a safe local execution path for future web candidate-review actions. A reviewer
action payload should be loadable from JSON, applied to a registry copy, and written
as a preview artifact without mutating the source registry.

## Acceptance

- CLI can run a review action preview without requiring `--fund-code`.
- The preview output includes the original action, mutation safety metadata, summary,
  and result registry.
- The default source registry file is never modified.
- Tests cover approve, reject/defer summary behavior, validation errors, and CLI output.
