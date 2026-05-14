# Review Action Persistence

## Goal

Add an explicit, guarded registry persistence workflow for human-approved
candidate review actions.

## Acceptance

- Persistence reuses the same review action payload as preview.
- The default path writes a new registry output file and does not mutate the source registry.
- In-place registry overwrite is rejected unless explicitly allowed.
- The action input file cannot be overwritten.
- CLI persistence does not require `--fund-code`.
