# R13 Source Digest Contracts

## Scope

Implement the current developer-owned source digest user stories in FNI:

- `MIK-233` Fresh narrative digest pipeline contract.
- `MIK-234` Entity resolution and deduplication contract for narrative sources.
- `MIK-232` Crawler adapter contract and robots/rate-limit policy.
- `MIK-228` Today's narrative monitoring digest requirement.

## Acceptance

- Build a deterministic fresh narrative digest from gateway probe/source-event payloads.
- Emit machine-readable JSON and canonical Chinese HTML output.
- Expose the digest through the product shell route registry and generated artifact browser.
- Keep fixture tests network-free and disallow dynamic browser rendering unless later approved.
- Preserve the repo boundary: FNI consumes gateway source events and does not implement live provider crawling.

## Verification

- Focused TDD tests for digest contracts and product shell integration.
- Full project test suite, lint, and diff whitespace checks.
