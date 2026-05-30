# Round 8 Interactive Product Shell & Release Packaging Plan - 2026-05-30

## Capability

Round 8 turns separate CLI and Chinese HTML outputs into one coherent local product entry point. A user should be able to open a product shell, navigate the major FNI/Narrative Service surfaces, inspect generated artifacts, see configuration/preflight state, and run a deterministic local demo/release validation.

## Product Goal

The product should stop feeling like a collection of scripts and reports. It should feel like a local intelligence console with clear navigation:

- Narrative Radar
- Narrative quality audit
- Portfolio/fund narrative workspace
- Production readiness assistant
- Generated artifacts
- Configuration and preflight status

This is still not a hosted SaaS, trading system, brokerage integration, or social scraping project.

## PM Requirements

### MIK-159 - PM Parent

`[PM-R8] Product requirement pack for interactive product shell and release packaging`

Users should be able to open one product shell and run the system through repeatable local release commands.

### MIK-161 - Integrated Local Product Shell Navigation

Provide one local product entry point for major product surfaces.

Acceptance focus:

- shell opens from a documented local command
- major surfaces are navigable
- live/fixture/degraded/generated-artifact surfaces are clearly labeled
- no client-side recalculation of radar, quality, or portfolio metrics

### MIK-162 - Artifact Browser And Run History

Expose generated JSON/HTML artifacts and the run context that produced them.

Acceptance focus:

- index existing output artifacts
- link to HTML and JSON
- show run time, status, warnings, data freshness, and source mode
- avoid secrets or raw provider tokens

### MIK-163 - Operational Control Panel And Config Preflight

Expose service/config readiness without leaking credentials.

Acceptance focus:

- show gateway, Narrative Service, and FNI config state
- redact secrets
- link to validation commands and runbooks
- failed config does not crash the shell

### MIK-164 - One-Command Local Release Package

Provide a repeatable local demo/release path.

Acceptance focus:

- one documented startup/check command
- startup order for gateway, Narrative Service, and FNI shell
- deterministic demo mode without live credentials
- verification command proves shell and core artifacts are reachable

## Architect Requirements

### MIK-160 - Architect Parent

`[ARCH-R8] Architecture requirement pack for interactive product shell and release packaging`

The shell must integrate existing service/API/artifact surfaces without moving provider access, narrative scoring, or fund aggregation into frontend code.

### MIK-165 - Product Shell Route And Data-Source Contract

Define route ownership and data-source types.

Required concepts:

- route registry
- owner service
- data source type: live API, generated artifact, fixture/demo
- freshness/degradation metadata
- no client-side score recomputation

### MIK-166 - Artifact Index And Manifest Contract

Define how generated artifacts are indexed and displayed.

Required concepts:

- artifact id/type/surface
- generated time and run id
- JSON/HTML paths
- status and warning count
- source mode and freshness status
- stale/superseded marker

### MIK-167 - Local Release Orchestration And Verification Contract

Define startup, deterministic demo mode, optional live mode, and verification.

Required concepts:

- startup order
- required/optional services
- redacted environment checks
- deterministic demo mode without live credentials
- release verification command and expected outputs

### MIK-168 - Product Shell Acceptance And Demo Checklist

Define a runnable acceptance checklist.

Required checks:

- shell opens
- major routes render
- artifact browser links work
- config preflight redacts secrets
- release command generates manifest

## Dependency Plan

- MIK-161 is blocked by MIK-165.
- MIK-162 is blocked by MIK-166.
- MIK-163 is blocked by MIK-165 and MIK-167.
- MIK-164 is blocked by MIK-167 and MIK-168.

## Recommended Developer Order

1. MIK-165: route and data-source contract.
2. MIK-166: artifact index and manifest contract.
3. MIK-161 + MIK-162: shell navigation and artifact browser.
4. MIK-167: local release orchestration.
5. MIK-163: operational config/preflight panel.
6. MIK-168 + MIK-164: acceptance checklist and one-command local release package.

## Non-Goals

- no hosted multi-tenant SaaS
- no external auth implementation
- no brokerage integration
- no trading workflow
- no AI prediction
- no social scraping
- no browser anti-bot work

## Acceptance Gate

Round 8 is accepted when a user can start the local product shell, navigate all major product surfaces, browse generated artifacts, see redacted config/preflight status, and run one deterministic release/demo validation command without live provider credentials.
