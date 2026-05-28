# Task Brief

## Linear

- Issue: MIK-42
- Title: [ARCH-P0] Narrative Service API contract and versioning rules
- Project: Fund Narrative Intelligence

## Goal

Make the Narrative Service API contract explicit enough for FNI and future
developer chats to consume the service through HTTP contracts rather than
Python imports.

## Acceptance Focus

- `config/narrative_service_contract.yaml` declares endpoint paths, normalized
  envelope fields, versioning policy, compatibility rule, and error semantics.
- The conformance probe validates every declared endpoint against the required
  envelope.
- The runbook documents endpoint behavior, versioning, error semantics, trust
  rules, and non-goals.
- FNI report entry points do not import `stock_narrative_service` internals.
