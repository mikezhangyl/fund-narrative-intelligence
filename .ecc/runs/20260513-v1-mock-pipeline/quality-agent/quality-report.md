# Quality Report

## Status

Passed with residual risks.

## Review Scope

Parent review of the working tree because sub-agent spawning was not allowed by the active Codex tool policy without an explicit user request for delegated or parallel agent work.

## Checks

- Tests pass with `python -m pytest -q`.
- Acceptance command passes with `python -m src.main --fund-code 000001`.
- Invalid fund code returns non-zero.
- Real provider mode degrades to mock provider and records a degradation event.
- Generated Markdown and HTML reports include the non-investment-advice disclaimer.
- Raw and scoring JSON artifacts are valid JSON.

## Findings

No blocking findings.

## Residual Risks

- Numeric coverage was not measured because `pytest-cov` and `coverage` are unavailable.
- Mock fixtures are not real market data.
- HTML report is intentionally simple and not a workspace UI.
