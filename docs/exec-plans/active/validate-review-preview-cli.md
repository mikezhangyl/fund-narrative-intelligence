# Validate Review Preview CLI

## Goal

Expose review-action preview artifact validation through the CLI so candidate
review previews can be checked without applying or persisting an action.

## Acceptance

- CLI validates a preview JSON file and exits `0` on success.
- Malformed preview files produce controlled validation errors.
- The command does not require `--fund-code`.
