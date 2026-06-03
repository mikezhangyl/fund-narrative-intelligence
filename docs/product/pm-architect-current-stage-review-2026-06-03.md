# PM/Architect Current Stage Review - 2026-06-03

Canonical readable artifact:
`docs/product/pm-architect-current-stage-review-2026-06-03.html`

## Review Scope

This review evaluates whether current FNI `main` is ready for the next stage
from a product/architecture acceptance perspective.

Reviewed areas:

- product shell;
- real narrative data entry point;
- source quality surface;
- gateway boundary;
- current generated artifacts and whether they support the next stage.

Current branch state at review time:

- branch: `main`;
- status: clean and aligned with `origin/main`;
- recent relevant commits include release readiness, workspace persistence,
  fresh narrative digest, source investigation gate pack, Tushare news smoke,
  provider evaluation, and HTML localization.

## Verification

Targeted verification passed:

```bash
uv run pytest tests/test_product_shell.py \
  tests/test_product_shell_release.py \
  tests/test_product_shell_source_quality.py \
  tests/test_product_shell_workspace_store.py \
  tests/test_fresh_narrative_digest.py \
  tests/test_narrative_source_gateway_consumer.py \
  tests/test_narrative_source_boundary.py \
  tests/test_tushare_news_permission_smoke.py \
  tests/test_source_investigation_gate_pack.py -q
```

Result:

- `60 passed`

Targeted lint passed:

```bash
uv run ruff check src/product_shell \
  src/market_data/providers/narrative_source_gateway.py \
  src/scanners/source_governance.py \
  src/scanners/source_schema_v2.py \
  src/scanners/source_reliability.py \
  scripts/run_product_shell_release_check.py \
  scripts/run_fresh_narrative_digest.py \
  scripts/run_tushare_news_permission_smoke.py \
  scripts/run_source_investigation_gate_pack.py \
  tests/test_product_shell.py \
  tests/test_product_shell_release.py \
  tests/test_product_shell_source_quality.py \
  tests/test_fresh_narrative_digest.py \
  tests/test_tushare_news_permission_smoke.py \
  tests/test_source_investigation_gate_pack.py
```

Result:

- `All checks passed`

## Acceptance Summary

Current FNI is accepted as a next-stage development base.

It now has enough product shell, artifact visibility, release preflight,
source-quality disclosure, and gateway boundary enforcement to support the next
developer phase.

It is not yet a live narrative discovery product. The current state is best
described as:

> local product console + artifact-backed narrative data + source-quality
> governance + gateway consumer contracts.

## Findings

### Finding 1 - Product shell is now usable for local demo/review

Status: accepted.

Evidence:

- `outputs/product_shell/round8-current/index.html`
- `outputs/product_shell/round8-current/artifact_browser.html`
- `outputs/product_shell/round8-current/config_preflight.html`
- `outputs/product_shell/round8-current/release_manifest.html`
- `outputs/product_shell/round8-current/acceptance_checklist.html`

Observed artifact state:

- `product_shell.json` reports 23 routes, 504 indexed artifacts, 15
  narratives, 56 stock mappings, and 1 saved workspace view.
- `acceptance_checklist.json` status is `pass`.
- `release_manifest.json` status is `ok`.
- `config_preflight.json` status is `ok` in demo mode and correctly states that
  preflight is not a provider smoke.

Review decision:

- This satisfies the local product shell goal for next-stage development.
- It is acceptable for Developer to build additional product surfaces on top of
  this shell.

### Finding 2 - Real narrative data entry exists, but it is not live discovery

Status: accepted with caveat.

Evidence:

- `outputs/product_shell/round8-current/narrative_data.html`
- `outputs/product_shell/round8-current/narrative_data.json`

The entry point is useful because it exposes existing Narrative Service / FNI
artifacts in one place. It includes:

- reviewed narrative registry;
- stock-to-narrative mappings;
- evidence packs;
- quality audit;
- service conformance;
- provider smoke.

Important caveat:

- This is "real existing artifact data", not a guaranteed current live market
  narrative feed.
- The current narrative data snapshot has service-backed evidence, but the
  fresh external source-event chain still depends on gateway source routes and
  live source feasibility.

Review decision:

- Good enough for the next product stage.
- Not enough to claim that FNI can discover today's real-world narratives by
  itself.

### Finding 3 - Source quality surface is useful and correctly degraded

Status: accepted with follow-up.

Evidence:

- `outputs/product_shell/round8-current/source_quality_dashboard.html`
- `outputs/product_shell/round8-current/source_quality_dashboard.json`
- `outputs/source_governance/2026-06-01-mik-229/source_governance_report.html`
- `outputs/source_reliability/2026-06-01-mik-231/source_reliability_report.html`
- `outputs/source_schema_v2/2026-06-01-mik-230/source_schema_v2_report.html`
- `outputs/narrative_source_gateway_probe/current/narrative_source_gateway_probe.html`

Observed dashboard state:

- status: `degraded`;
- source count: 3;
- trusted fact count: 1;
- degraded/blocked source count: 2;
- missing artifact count: 0.

This is the right product behavior. The dashboard should not hide source risk.
It correctly shows:

- SEC EDGAR filings as `trusted_fact`;
- public industry media candidate as blocked until robots/TOS and pacing are
  reviewed;
- forbidden social scrape as blocked.

Follow-up:

- The dashboard currently relies mainly on governance/reliability decisions and
  does not yet fully promote gateway-probe-only source groups into first-class
  rows. For example, a gateway probe can show `social_heat` missing while the
  dashboard still only shows the broader governance rows.

Review decision:

- Accepted for next-stage development.
- Before user-facing source operations, the dashboard should show every gateway
  source kind as its own coverage row.

### Finding 4 - Gateway boundary is correctly enforced

Status: accepted.

Evidence:

- `tests/test_narrative_source_boundary.py`
- `src/market_data/providers/narrative_source_gateway.py`
- `scripts/run_narrative_source_gateway_probe.py`
- `docs/product/market-data-gateway-boundary.md`
- `docs/product/round13-narrative-source-deep-mining-plan-2026-06-01.md`

Current product boundary:

- FNI owns product surfaces, reports, artifacts, contracts, and probes.
- `stock-data-gateway` owns external source acquisition, credentials, rate
  limits, cache, adapters, and source-event ingestion.
- FNI does not add new SEC/CNINFO/news/social direct source adapters.

Review decision:

- Boundary is good and should be preserved.
- Developer should not implement external source collection inside FNI.

### Finding 5 - Fresh narrative digest is an interface, not a proven live feed

Status: accepted as contract, not accepted as live product capability.

Evidence:

- `outputs/fresh_narrative_digest/current/fresh_narrative_digest.html`
- `outputs/fresh_narrative_digest/current/fresh_narrative_digest.json`

Observed state:

- digest status: `ok`;
- digest item count: 3;
- contract explicitly says provider access is not allowed from FNI;
- trust state remains `candidate_untrusted`.

Review decision:

- The digest is a valid next-stage UI/contract surface.
- It should not be presented as a production live discovery feature until
  gateway source events are live, current, and coverage-scored.

### Finding 6 - Tushare news is blocked by live gateway availability in current artifact

Status: not a product blocker, but a next-stage live-data blocker.

Evidence:

- `outputs/tushare_news_permission_smoke/current/tushare_news_permission_smoke.html`
- `outputs/tushare_news_permission_smoke/current/tushare_news_permission_smoke.json`

Observed state:

- status: `Blocked`;
- gateway configured: true;
- gateway provider loaded: true;
- all six source values failed because the local gateway request was refused.

Review decision:

- This is acceptable for deterministic local release because release preflight
  correctly does not run provider smoke.
- It blocks any claim that current FNI has a working live Tushare news source.
- Next live-data work should be coordinated through gateway, not FNI.

### Finding 7 - Current artifacts support next-stage development

Status: accepted.

The current artifact set is sufficient for:

- local product demo;
- source-quality review;
- artifact browsing;
- release readiness;
- workspace persistence;
- fresh digest UI/contract development;
- gateway conformance display;
- future source-quality drill-down.

The current artifact set is not sufficient for:

- production live narrative discovery;
- paid provider trial acceptance;
- social/community heat production use;
- trusted automatic narrative promotion;
- user-facing claims that today's narrative feed is complete.

## Next Stage Recommendation

Developer should now build product workflow on top of the shell, not add new
external source adapters.

Recommended order:

1. Make source-quality dashboard coverage complete:
   - show every gateway probe source kind as a first-class row;
   - distinguish `ok`, `missing`, `degraded`, `blocked`, and `not_configured`;
   - preserve gateway ownership boundary.
2. Turn the fresh narrative digest into a product surface:
   - render candidate state, evidence links, trust state, freshness, and
     degradation;
   - keep all items `candidate_untrusted` unless trusted evidence promotion
     rules are satisfied.
3. Add live conformance lane:
   - deterministic release remains credential-free;
   - live source checks become explicit operator action;
   - failed gateway/provider checks appear as product artifacts, not hidden CLI
     noise.
4. Start deeper workflow only after this:
   - narrative drill-down;
   - source-event timeline/search;
   - review queue integration;
   - workspace persistence around saved views and review state.

## Final Decision

Accepted for next-stage development.

The product is ready to move from "artifact-backed local shell" toward
"operator workflow and source-aware narrative review." It is not ready to be
called a live narrative intelligence product until gateway source-events and
live source coverage are verified.
