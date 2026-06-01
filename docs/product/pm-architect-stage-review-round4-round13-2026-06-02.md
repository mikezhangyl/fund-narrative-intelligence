# PM/Architect Stage Review - Round 4 to Round 13 - 2026-06-02

Canonical readable artifact:
`docs/product/pm-architect-stage-review-round4-round13-2026-06-02.html`

## Review Scope

This review covers the current local `main` branch after the Round 4 to Round
13 development work was merged locally. The review focuses on visible product
artifacts, acceptance documents, gateway/FNI boundary cleanup, and the next
developer sequence in Linear.

Reviewed capabilities:

- local product shell and artifact browser;
- real generated artifact display;
- source governance, source schema v2, and reliability scoring;
- narrative source gateway consumer contract and probes;
- boundary cleanup that moves real SEC/CNINFO/news/social source-event
  collection back to `stock-data-gateway`.

Verification performed:

```bash
uv run pytest tests/test_product_shell.py \
  tests/test_narrative_source_gateway_consumer.py \
  tests/test_source_governance_model.py \
  tests/test_source_schema_v2.py \
  tests/test_source_reliability_scoring.py -q

uv run ruff check src/product_shell \
  src/market_data/providers/narrative_source_gateway.py \
  src/scanners/source_governance.py \
  src/scanners/source_schema_v2.py \
  src/scanners/source_reliability.py \
  tests/test_product_shell.py \
  tests/test_narrative_source_gateway_consumer.py \
  tests/test_source_governance_model.py \
  tests/test_source_schema_v2.py \
  tests/test_source_reliability_scoring.py
```

Result:

- `33 passed`
- `ruff` passed

Additional documents inspected:

- `docs/product/round8-product-shell-artifact-browser-acceptance-2026-05-31.md`
- `docs/product/round8-interactive-product-shell-release-plan-2026-05-30.md`
- `docs/product/round13-narrative-source-deep-mining-plan-2026-06-01.md`
- `.ecc/runs/20260601-real-narrative-data-shell/run-state.json`
- `.ecc/runs/20260602-fni-narrative-source-boundary-cleanup/run-state.json`

## PM Conclusion

The current `main` is directionally correct and should be treated as a valid
stage checkpoint. The largest product correction has been made: FNI is no
longer responsible for direct external source acquisition. FNI now owns product
surfaces, reports, probes, contracts, and consumption of gateway-provided
source events.

The product is not yet an end-to-end narrative intelligence console. It is now
a local, artifact-backed shell with stronger source-governance foundations and
clearer service boundaries.

## Linear Issues Recommended Done

These issues can be marked `Done` if Linear does not already show them as done.

| Issue | Review decision | Reason |
| --- | --- | --- |
| `MIK-165` | Done | Route/data-source contract exists in the product shell route registry and preserves service ownership boundaries. |
| `MIK-166` | Done | Artifact index and manifest contract exist and are rendered into JSON/Chinese HTML artifacts. |
| `MIK-161` | Done | Local product shell navigation exists with major surfaces labeled by data mode and ownership. |
| `MIK-162` | Done | Artifact browser indexes generated JSON/HTML outputs and links to reviewable artifacts. |
| `MIK-229` | Done | Source governance/compliance model exists with tests and explicit gateway ownership of acquisition. |
| `MIK-230` | Done | Narrative source-event/schema v2 exists with required quality and trust fields. |
| `MIK-231` | Done | Source reliability, licensing, and anti-bot scoring exists and is deterministic/tested. |
| `MIK-250` | Done | FNI gateway consumer contract/probes exist for provider-neutral narrative source routes. |

## Foundation Complete, Product Not Complete

These should not be closed as full product outcomes yet. They are either
partially implemented or need visible UI/operation acceptance.

| Area | Current state | Missing acceptance |
| --- | --- | --- |
| Round 8 config/preflight | The shell has route and artifact foundations. | Redacted gateway/Narrative/FNI config preflight panel still needs a visible shell surface. |
| Round 8 release packaging | Build commands exist for generated shell artifacts. | One-command local release/demo validation and acceptance checklist still need to be productized. |
| Narrative Radar UI | Contracts and preview artifacts exist. | The bubble chart/trend surface is not yet a polished product view inside the shell. |
| Today/recent narrative digest | Requirements are defined. | The user-facing digest is not yet a visible workflow backed by gateway source events. |
| Source governance UI | Governance/schema/reliability logic exists. | A single operator-readable dashboard for source trust, license, anti-bot risk, and degradation is still missing. |
| Live gateway source checks | FNI consumer contract and probes exist. | Real gateway routes still need live conformance once `stock-data-gateway` implements the source-event endpoints. |

## Issues To Rewrite Or Keep Outside FNI Dev

The following should not be implemented as direct FNI external-source adapters.
They either belong in `stock-data-gateway` or should stay as PM/Architect
investigation work until provider feasibility is proven.

| Issue | Recommended state | Reason |
| --- | --- | --- |
| `MIK-235` | Closed/moved to gateway | SEC EDGAR acquisition belongs in gateway. |
| `MIK-236` | Closed/moved to gateway | CNINFO acquisition/classification belongs in gateway. |
| `MIK-237` | Closed/moved to gateway | Public news cleanup/source-quality acquisition belongs in gateway. |
| `MIK-238` | Closed/moved to gateway | Stocktwits/social heat collection belongs in gateway. |
| `MIK-246` | Closed/moved to gateway or replaced | Storage schema tied to source acquisition should follow the gateway/lakehouse design. |
| `MIK-247` | Closed/moved to gateway or replaced | Raw zone/blob manifest is gateway/lakehouse infrastructure, not FNI product logic. |
| `MIK-249` | Closed/moved to gateway or replaced | Docker lakehouse runtime is a gateway/lakehouse concern unless FNI is only consuming it. |
| `MIK-224` to `MIK-227` | Keep as PM investigation | Provider evaluation and access feasibility should remain PM/Architect tracked until sources are proven. |
| `MIK-239` to `MIK-242` | Keep as PM investigation | Live smoke/trial/access investigation should prove data availability before Developer implementation. |

## Next Developer Order

The next developer work should avoid direct source acquisition in FNI. The
recommended order is:

1. Finish Round 8 local product completion:
   - `MIK-167`: local release orchestration and verification contract;
   - `MIK-163`: operational control panel and config preflight;
   - `MIK-168`: product shell acceptance/demo checklist;
   - `MIK-164`: one-command local release package.
2. Integrate source governance into the product shell:
   - add a visible source governance/reliability dashboard that consumes the
     existing governance/schema/reliability artifacts;
   - show source trust, license scope, anti-bot risk, degradation, and owner
     boundary in one Chinese HTML surface.
3. After gateway implements narrative source-event routes, run FNI live
   conformance:
   - use `MIK-250` contracts/probes as the acceptance gate;
   - render probe results into the artifact browser/product shell;
   - do not add new FNI direct external-source adapters.
4. Start Round 9 only after Round 8 shell/release is closed:
   - `MIK-180` plus `MIK-177` for workspace persistence and saved views.

## PM Caveats

- This review did not run live gateway/provider checks. It verified the FNI
  consumer contract, product-shell artifacts, and source governance logic.
- Some historical `.ecc/runs/*/run-state.json` files still show stale
  intermediate statuses such as `ready_for_quality`. The current merged code and
  targeted tests are the source of truth for this stage review.
- Local `main` is ahead of `origin/main`; this review does not imply the remote
  branch has the same state.

## Merge/Acceptance Decision

Accepted as a stage checkpoint.

The immediate PM/Architect decision is:

- close the issues listed under "Recommended Done";
- keep partial product issues open until their visible shell/release acceptance
  is complete;
- keep external source acquisition in `stock-data-gateway`;
- continue FNI development on product shell completion, source-quality display,
  gateway conformance, and then workspace persistence.
