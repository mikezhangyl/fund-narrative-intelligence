# Real Enriched Acceptance

## Goal

Add one strict live-provider acceptance gate for the combined enriched path:
Eastmoney holdings, CNINFO announcements/evidence, market quotes, and derived
signals.

## Scope

- Run the report pipeline with `--provider-mode eastmoney`,
  `--include-cninfo-announcements`, and `--include-market-quotes`.
- Validate raw, scoring, review queue, manifest, Markdown, and HTML artifacts.
- Require non-mock holdings, announcements, market quote, and derived-signal
  provider layers.
- Require both `cninfo_announcement` and `market_quote` derived signals.
- Keep registry, mapping, base evidence, and base signal layers explicitly
  mock-backed until future provider work replaces them.

## Non-Goals

- Do not make this live-provider check a CI gate.
- Do not replace fixture registry or mapping layers.
- Do not add web UI interaction yet; artifacts only need to remain web-ready.

## Acceptance

```bash
python scripts/validate_real_enriched_acceptance.py --output-dir outputs/real_enriched_161725
```

Expected result:

- Fresh Eastmoney holdings are present.
- CNINFO announcements and converted evidence are present.
- Real market quote rows are present.
- Derived signals include both announcement and quote sources.
- Reports disclose the mixed real + Mock fixture foundation.
