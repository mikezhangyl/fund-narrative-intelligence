# Task Brief

## Goal

Complete M21 Linear stories in order:

MIK-288 -> MIK-289 -> MIK-290 -> MIK-291 -> MIK-292 -> MIK-293 -> MIK-294

The work starts after MIK-287 reconciled local `main` with `origin/main`.

## Scope

- Keep FNI as the consumer/reporting layer for Gateway narrative source events.
- Do not add direct SEC/CNINFO/news/social upstream calls inside FNI.
- Produce JSON plus Chinese HTML for reader-facing artifacts.
- Use TDD checkpoint slices and commit after each coherent user-story capability.

## MIK-288 Checkpoint

Implemented the live/fixture Gateway source-event acceptance smoke by hardening
`scripts/run_narrative_source_gateway_probe.py`.

Key behavior:

- Report version is now `narrative-source-gateway-acceptance-v2`.
- Each source kind receives an `acceptance_status`: `pass`, `degraded`, `no_data`,
  `missing_route`, `blocked`, or `schema_mismatch`.
- The report validates envelope, rows, source_kind, trust_tier, source_quality,
  degradation_events, pagination metadata, cache metadata, and owner_service.
- `owner_service` is reported as `stock-data-gateway`; if Gateway omits the field,
  `owner_service_source` is `fni_contract_default`.
- FNI still calls only the unified Gateway route and does not call external upstreams.

Artifacts generated locally:

- `outputs/narrative_source_gateway_probe/2026-06-08-m21-fixture/narrative_source_gateway_probe.json`
- `outputs/narrative_source_gateway_probe/2026-06-08-m21-fixture/narrative_source_gateway_probe.html`
- `outputs/narrative_source_gateway_probe/2026-06-08-m21-live/narrative_source_gateway_probe.json`
- `outputs/narrative_source_gateway_probe/2026-06-08-m21-live/narrative_source_gateway_probe.html`

Verification:

- `uv run pytest tests/test_narrative_source_gateway_consumer.py -q`: 9 passed.
- `uv run pytest tests/test_product_shell_source_quality.py tests/test_fresh_narrative_digest.py tests/test_narrative_source_coverage_gap.py -q`: 21 passed.
- `uv run ruff check scripts/run_narrative_source_gateway_probe.py src/market_data/providers/narrative_source_gateway.py tests/test_narrative_source_gateway_consumer.py`: passed.
- Fixture acceptance: 6 pass, 1 degraded, 0 blocking.
- Live acceptance against local Gateway on `127.0.0.1:8700`: 2 pass, 2 degraded, 3 no_data, 0 blocking.

## MIK-289 Checkpoint

Implemented a source-derived candidate review queue without changing the older
fund mapping review queue.

Key behavior:

- Added `src/modules/narrative_review/source_queue.py`.
- Added `scripts/run_source_candidate_review_queue.py`.
- Input is existing `narrative_candidate_inbox`; optional `fresh_narrative_digest`
  enriches freshness state and related symbols/markets.
- Output version is `source-candidate-review-queue-v1`.
- Each row includes candidate_id, title/topic, candidate_state, freshness_state,
  source_event_count, source_kind_mix, newest_event_time, related symbols/markets,
  trust_tier_summary, degradation_flags, review_priority, and stable evidence detail links.
- Filters are supported for source kind, trust tier, freshness state, market, and candidate state.
- No row can mark a candidate trusted; `trusted_promotion_allowed` is always false.
- Chinese HTML separates official-backed, context-only, and heat-only candidates.

Artifacts generated locally:

- `outputs/source_candidate_review_queue/2026-06-08-m21-fixture/source_candidate_review_queue.json`
- `outputs/source_candidate_review_queue/2026-06-08-m21-fixture/source_candidate_review_queue.html`
- `outputs/source_candidate_review_queue/2026-06-08-m21-live/source_candidate_review_queue.json`
- `outputs/source_candidate_review_queue/2026-06-08-m21-live/source_candidate_review_queue.html`

Verification:

- `uv run pytest tests/test_source_candidate_review_queue.py -q`: 4 passed.
- `uv run pytest tests/test_fresh_narrative_digest.py tests/test_candidate_review_queue.py -q`: 13 passed.
- `uv run ruff check scripts/run_source_candidate_review_queue.py src/modules/narrative_review/source_queue.py tests/test_source_candidate_review_queue.py`: passed.
- Fixture queue from MIK-288 fixture probe: 5 candidates, 3 official-backed, 2 context-only, 0 trusted.
- Live queue from MIK-288 live probe: 2 candidates, 1 official-backed, 1 context-only, 0 trusted.

## MIK-290 Checkpoint

Implemented candidate evidence drill-down for one source-derived candidate.

Key behavior:

- Added `src/modules/narrative_review/source_evidence.py`.
- Added `scripts/run_candidate_evidence_detail.py`.
- Input is `source_candidate_review_queue.json` plus a Gateway probe/source-event payload.
- Output version is `candidate-evidence-detail-v1`.
- Evidence rows preserve source_event_id and show source URL, title, event time,
  provider/domain, source_quality, retention/extraction status, freshness state,
  degradation_events, and promotion evidence role.
- Events are grouped by source_kind and trust tier.
- Missing source_event_id references remain visible as `event_status=missing`
  with `SOURCE_EVENT_NOT_FOUND`; FNI does not invent missing source facts.
- Context-only and heat-only evidence are labeled insufficient for trusted promotion alone.
- The artifact remains read-only and does not perform trusted promotion.

Artifacts generated locally:

- `outputs/candidate_evidence/2026-06-08-m21-fixture/CAND_B4F3DE8BD1.json`
- `outputs/candidate_evidence/2026-06-08-m21-fixture/CAND_B4F3DE8BD1.html`
- `outputs/candidate_evidence/2026-06-08-m21-live/CAND_26E13C7A6D.json`
- `outputs/candidate_evidence/2026-06-08-m21-live/CAND_26E13C7A6D.html`

Verification:

- `uv run pytest tests/test_candidate_evidence_detail.py -q`: 4 passed.
- `uv run pytest tests/test_candidate_evidence_detail.py tests/test_source_candidate_review_queue.py -q`: 8 passed.
- `uv run ruff check scripts/run_candidate_evidence_detail.py src/modules/narrative_review/source_evidence.py tests/test_candidate_evidence_detail.py`: passed.
- Fixture evidence detail: 1 official event, 0 missing, 0 degraded.
- Live evidence detail: 2 official events, 0 missing, 0 degraded.

## MIK-291 Checkpoint

Implemented append-only source candidate review action ledger.

Key behavior:

- Added `src/modules/narrative_review/source_action_ledger.py`.
- Added `scripts/run_source_review_action_ledger.py`.
- Supported actions: `watch`, `needs_more_evidence`, `reject`, `defer`,
  `ready_for_trust_preflight`.
- Records include action_id, candidate_id, actor placeholder, action, reason,
  created_at, idempotency_key, source_artifact_refs, previous_candidate_state,
  new_candidate_state, and trusted_promotion_allowed=false.
- Re-running with the same idempotency key does not duplicate records.
- Terminal `rejected` state rejects later non-idempotent actions.
- The ledger never emits a trusted state or promotion action.
- JSON and Chinese HTML summary artifacts are generated.

Artifacts generated locally:

- `outputs/source_review_action_ledger/2026-06-08-m21-live/ledger.json`
- `outputs/source_review_action_ledger/2026-06-08-m21-live/source_review_action_ledger.json`
- `outputs/source_review_action_ledger/2026-06-08-m21-live/source_review_action_ledger.html`

Verification:

- `uv run pytest tests/test_source_review_action_ledger.py -q`: 9 passed.
- `uv run pytest tests/test_source_review_action_ledger.py tests/test_candidate_evidence_detail.py tests/test_source_candidate_review_queue.py -q`: 17 passed.
- `uv run ruff check scripts/run_source_review_action_ledger.py src/modules/narrative_review/source_action_ledger.py tests/test_source_review_action_ledger.py`: passed.
- Live ledger action: `ready_for_trust_preflight` for `CAND_26E13C7A6D`, 1 record, 0 trusted actions.
- Idempotency replay check: second run with same key kept total_action_count=1 and idempotent_replay_count=1.

## MIK-292 Checkpoint

Implemented read-only trust preflight for source-derived candidates.

Key behavior:

- Added `src/modules/narrative_review/source_trust_preflight.py`.
- Added `scripts/run_source_trust_preflight.py`.
- Input is source candidate review queue, candidate evidence detail, and review action ledger.
- Output version is `source-trust-preflight-v1`.
- Criteria: official/primary source presence, source diversity, entity/symbol clarity,
  freshness, degradation/contradiction flags, review action state, and evidence metadata.
- Result statuses are `pass`, `warning`, or `fail`.
- Context-only and heat-only candidates fail with explicit Chinese reasons.
- Official-backed candidates can pass only when evidence metadata and
  `ready_for_trust_preflight` review action state are present.
- The report is read-only and never performs automatic promotion, LLM judgment, or investment conclusion.

Artifacts generated locally:

- `outputs/source_trust_preflight/2026-06-08-m21-live/CAND_26E13C7A6D.json`
- `outputs/source_trust_preflight/2026-06-08-m21-live/CAND_26E13C7A6D.html`

Verification:

- `uv run pytest tests/test_source_trust_preflight.py -q`: 5 passed.
- `uv run pytest tests/test_source_trust_preflight.py tests/test_source_review_action_ledger.py tests/test_candidate_evidence_detail.py -q`: 18 passed.
- `uv run ruff check scripts/run_source_trust_preflight.py src/modules/narrative_review/source_trust_preflight.py tests/test_source_trust_preflight.py`: passed.
- Live preflight for `CAND_26E13C7A6D`: overall `warning`; official source, review action, degradation, and metadata checks passed; source diversity and freshness returned warnings.

## MIK-293 Checkpoint

Implemented standalone operator workflow linking daily digest to candidate review.

Key behavior:

- Added `src/modules/narrative_review/source_operator_workflow.py`.
- Added `scripts/run_source_operator_workflow.py`.
- Input is `fresh_narrative_digest.json`, `source_candidate_review_queue.json`,
  and optional preflight index.
- Output version is `source-operator-workflow-v1`.
- Each digest item links to queue row, candidate evidence detail, and trust preflight path when a candidate exists.
- Stable links use `source_candidate_review_queue.html#<candidate_id>`,
  `candidate_evidence/<candidate_id>.html`, and `source_trust_preflight/<candidate_id>.html`.
- Next operator actions include `inspect_evidence`, `watch`, `request_more_evidence`,
  and `run_trust_preflight`.
- Degradation/source trust labels are preserved; missing source-event input remains visible as degraded input state.
- No digest item implies trust without review/preflight.

Artifacts generated locally:

- `outputs/source_operator_workflow/2026-06-08-m21-live/source_operator_workflow.json`
- `outputs/source_operator_workflow/2026-06-08-m21-live/source_operator_workflow.html`

Verification:

- `uv run pytest tests/test_source_operator_workflow.py -q`: 4 passed.
- `uv run pytest tests/test_source_operator_workflow.py tests/test_source_trust_preflight.py tests/test_source_candidate_review_queue.py -q`: 13 passed.
- `uv run ruff check scripts/run_source_operator_workflow.py src/modules/narrative_review/source_operator_workflow.py tests/test_source_operator_workflow.py`: passed.
- Live workflow: 2 digest items, 2 linked candidates, 0 trusted implied.
