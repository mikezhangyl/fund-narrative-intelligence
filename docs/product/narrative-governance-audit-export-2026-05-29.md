# Narrative Governance Audit Export - 2026-05-29

## Scope

This slice implements the Round 2 MIK-59 product export for governance health
review outside the app.

The export is read-only. It does not clean up records, mutate registries, mutate
service ledgers, or perform trusted promotion.

## Entry Point

```bash
uv run python scripts/run_narrative_governance_audit_export.py \
  --registry-path data/fixtures/narrative_governance_registry.v1.json \
  --output-dir outputs/narrative_governance_audit/2026-05-29-mik-59-fixture
```

The default registry path is the reviewed narrative registry.

## Output

- JSON: `outputs/narrative_governance_audit/2026-05-29-mik-59-fixture/narrative_governance_audit_export.json`
- HTML: `outputs/narrative_governance_audit/2026-05-29-mik-59-fixture/narrative_governance_audit_export.html`

The export includes:

- Narrative id / candidate id
- Trust state
- Source count
- Review status
- Promotion decision
- Missing gates
- Latest reviewer
- PM-facing warnings
- Developer-facing warning codes
- CSV-friendly flattened fields

Promoted-looking seed records without service-ledger approval are flagged as
`missing_service_ledger_approval`.
