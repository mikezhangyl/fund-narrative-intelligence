# Round 4 Review Workflow State Machine - 2026-05-30

Canonical readable artifact:
`docs/product/round4-review-workflow-state-machine-2026-05-30.html`

Linear issues: `MIK-97`, `MIK-92`

Implemented service endpoints:

- `GET /api/v1/narratives/review-workflow/contract`
- `GET /api/v1/narratives/review-workflow`
- `GET /narratives/review`

The workflow now exposes candidate review state from candidate intake through
review action, non-mutating promotion preflight, and trusted promotion commit.
Review actions and failed promotions preserve `promotion_effect=none`; trusted
records are written only by the explicit promotion commit path.
