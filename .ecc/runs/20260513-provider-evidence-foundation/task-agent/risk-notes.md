# Risk Notes

- Eastmoney smoke still depends on a public network endpoint and can fail independently of local provider foundation logic.
- V1 does not yet ingest real evidence, news, valuation, announcements, or signal events.
- `provider_set_version` remains the existing V1 metadata default; the new `provider_foundation` object carries the more precise per-layer provenance.
- The Data Source Notice is implemented in report outputs; a future UI must preserve the same disclosure requirement.
