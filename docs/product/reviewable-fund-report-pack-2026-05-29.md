# Reviewable Fund Report Pack - 2026-05-29

## Scope

This slice implements the Round 2 MIK-58 workflow for building one static,
reviewable fund report pack from generated pipeline artifacts.

The pack is a Chinese HTML reader surface backed by JSON. It is for audit and
review workflow only; it does not provide portfolio recommendations, investment
advice, trading strategy, or predictions.

## Entry Point

```bash
uv run python scripts/run_reviewable_fund_report_pack.py \
  --artifact-root outputs/reviewable_fund_report_pack/2026-05-29-mik-58-pipeline \
  --output-dir outputs/reviewable_fund_report_pack/2026-05-29-mik-58-fixture \
  --reference-artifact fund_holding_exposure=fund_holding_exposure_report.html \
  --reference-artifact narrative_matrix=fund_narrative_exposure_matrix_report.html \
  --reference-artifact mapping_evidence_pack=mapping_evidence_pack_report.html \
  --reference-artifact change_monitor=fund_narrative_change_monitor_report.html
```

## Output

- JSON: `outputs/reviewable_fund_report_pack/2026-05-29-mik-58-fixture/reviewable_fund_report_pack.json`
- HTML: `outputs/reviewable_fund_report_pack/2026-05-29-mik-58-fixture/reviewable_fund_report_pack.html`

## Contents

The pack includes:

- Core artifact links from the `pipeline-artifact-manifest-v1` manifest.
- Reference links for fund holding exposure, narrative matrix, mapping evidence
  pack, and change monitor artifacts when supplied.
- Holding overview.
- Narrative exposure table.
- Source modes and data gap summary.
- Review Queue summary and entries.
- Trust disclosure showing `candidate_untrusted` outputs and disabled trusted
  promotion.

Missing gateway/service data is shown through manifest `warning_counts`,
provider source modes, and data quality rows.
