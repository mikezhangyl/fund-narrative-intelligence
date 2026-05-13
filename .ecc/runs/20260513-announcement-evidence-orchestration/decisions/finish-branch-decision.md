# Finish Branch Decision

## Decision

Keep and merge.

## Rationale

- The feature is explicitly opt-in and leaves default report behavior unchanged.
- Provider foundation disclosure now includes the `Announcements` layer when the option is enabled.
- Quality gates and live smoke checks pass.

## Follow-Up

Review generated announcement evidence on real A-share funds with non-empty CNINFO result windows before enabling signal generation from announcements.
