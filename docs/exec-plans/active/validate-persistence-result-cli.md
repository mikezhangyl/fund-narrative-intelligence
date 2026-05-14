# Validate Persistence Result CLI

## Goal

Expose persistence-result artifact validation through the CLI so audit records
can be checked by future CI, scripts, or web backend jobs.

## Acceptance

- CLI validates a persistence result JSON file and exits `0` on success.
- Missing or malformed persistence result files produce controlled validation
  errors.
- The command does not require `--fund-code`.
