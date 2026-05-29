# PM + Architect Acceptance Review - 2026-05-29

Review target: `codex/linear-fni-develop`

Reviewed by: PM + Architect role

## Decision

Status: not accepted for merge yet.

The branch is broadly healthy, but one blocking CLI-entry defect remains in the
human review workspace slice. Do not merge `codex/linear-fni-develop` into
`main` until the blocking defect below is fixed and re-verified.

## What Passed

Repository quality checks passed:

```bash
uv run ruff check .
uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests
git diff --check main...HEAD
uv run pytest -q
```

Observed result:

```text
519 passed, 1 skipped
```

Narrative Service acceptance passed:

```bash
uv run python scripts/validate_stock_narrative_service_acceptance.py
```

Observed result:

```text
status=completed
conformance_status=completed
endpoint_count=13
provider_smoke_status=completed
provider_smoke_source=narrative_service
fallback_smoke_status=completed
fallback_smoke_source=local_prototype
report_status=completed
report_narrative_source=narrative_service
```

Market data capability inventory smoke passed:

```bash
uv run python scripts/report_data_capabilities.py --format json --output outputs/data_capabilities/pm_arch_acceptance_inventory.json
uv run python scripts/report_data_capabilities.py --format html --output outputs/data_capabilities/pm_arch_acceptance_inventory.html
```

Observed inventory summary:

```text
dataset_row_count=26
group_count=8
status_label_counts.can_do=24
status_label_counts.unstable=2
```

Narrative review workspace functional smoke passed when `PYTHONPATH=.` was
provided and a local Narrative Service was running:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8891

PYTHONPATH=. uv run python scripts/run_narrative_review_workspace.py \
  --service-url http://127.0.0.1:8891 \
  --output-dir outputs/narrative_review_workspace/pm_arch_acceptance_service
```

Observed result:

```text
candidate_count=4
evidence_link_count=3
action_status=not_submitted
```

## Blocking Defect

Linear issue: `MIK-51`

Parent issue blocked: `MIK-38`

Title: Fix review workspace direct CLI invocation

Direct execution from the repository root fails before normal argument
validation:

```bash
uv run python scripts/run_narrative_review_workspace.py \
  --output-dir outputs/narrative_review_workspace/pm_arch_acceptance
```

Actual result:

```text
ModuleNotFoundError: No module named 'src'
```

Expected result:

The script should behave like other repo scripts. It should add `PROJECT_ROOT`
to `sys.path` before importing `src.*`, then proceed to normal argument
validation.

Without `--service-url` or `NARRATIVE_SERVICE_URL`, it may fail with the intended
message:

```text
--service-url or NARRATIVE_SERVICE_URL is required
```

It must not fail at import time.

## Required Fix

Update `scripts/run_narrative_review_workspace.py` so it bootstraps the repo
root before importing `src.config`.

Use the same pattern used by other repo scripts:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

This must appear before:

```python
from src.config import DEFAULT_OUTPUT_DIR
```

## Required Verification After Fix

Run:

```bash
uv run pytest tests/test_narrative_review_workspace.py -q
uv run python scripts/validate_stock_narrative_service_acceptance.py
uv run ruff check scripts/run_narrative_review_workspace.py tests/test_narrative_review_workspace.py
uv run python -m compileall -q scripts tests
git diff --check
```

Also run direct CLI smoke without `PYTHONPATH=.`:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8891

uv run python scripts/run_narrative_review_workspace.py \
  --service-url http://127.0.0.1:8891 \
  --output-dir outputs/narrative_review_workspace/pm_arch_acceptance_fixed
```

Expected smoke result:

```text
json=outputs/narrative_review_workspace/pm_arch_acceptance_fixed/narrative_review_workspace.json
html=outputs/narrative_review_workspace/pm_arch_acceptance_fixed/narrative_review_workspace.html
candidate_count>0
```

## PM Acceptance Notes

The implemented feature set mostly matches the intended PM roadmap:

- capability inventory exists and generates JSON/HTML;
- candidate detail endpoint exists;
- evidence detail endpoint exists;
- review workspace exists as CLI/HTML first, which is acceptable for MVP;
- provider/source disclosure exists in reports;
- trusted promotion workflow is explicit and gated;
- narrative trust states are disclosed.

The review workspace cannot be accepted while its direct CLI entrypoint fails,
because developer handoff and PM acceptance both assume repo scripts can be run
from the repository root without custom `PYTHONPATH`.

## Architect Acceptance Notes

The architecture direction is acceptable:

- FNI remains a consumer of gateway and Narrative Service contracts;
- Narrative Service exposes HTTP boundaries instead of requiring FNI imports;
- contract conformance is generated from `config/narrative_service_contract.yaml`;
- review actions, preflight, and promotion remain separate concepts;
- source/fallback/degraded diagnostics are now explicit.

The remaining defect is not an architecture blocker in design, but it is an
entrypoint consistency defect. Fixing it should not require changing service
contracts or report semantics.

## Communication Rule

Use this document as the canonical PM/Architect feedback artifact for this
acceptance cycle. Linear comments should point to this document rather than
duplicating detailed review text.
