# Fund Narrative Change Monitor - 2026-05-29

## Scope

This slice implements the Round 2 MIK-57 workflow for comparing a fund's current
narrative exposure snapshot against a previous snapshot.

The report is observational only. It does not provide buy/sell advice, price
prediction, or automatic causality claims.

## Entry Point

```bash
uv run python scripts/run_fund_narrative_change_monitor.py \
  --output-dir outputs/fund_narrative_change_monitor/2026-05-29-mik-57-fixture
```

By default, the script reads
`data/fixtures/fund_narrative_change_snapshots.v1.json`. It can also accept
separate `--previous-snapshot-path` and `--current-snapshot-path` inputs.

## Output

- JSON: `outputs/fund_narrative_change_monitor/2026-05-29-mik-57-fixture/fund_narrative_change_monitor_report.json`
- HTML: `outputs/fund_narrative_change_monitor/2026-05-29-mik-57-fixture/fund_narrative_change_monitor_report.html`

The report classifies:

- Added narratives
- Removed narratives
- Increased exposure
- Decreased exposure
- Concentration changes
- Data gaps

## Source And Trust Disclosure

The report includes holding source, previous/current narrative source, mapping
trust state, and data gaps. Fixture output remains `partial` because it
intentionally includes a gateway credential data gap.
