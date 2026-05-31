# Task Brief

## Linear

- Issue: MIK-250
- Title: [FNI-CONSUMER][R13] Narrative source gateway consumer contract and probes

## Scope

FNI must consume narrative source events only through provider-neutral
stock-data-gateway routes. This run adds the FNI-side contract entries, gateway
consumer client, conformance probe, and Chinese HTML/JSON reports for official
filings, official disclosures, news context, and social heat source events.

## Boundary

No new direct external SEC EDGAR, CNINFO, news, or Stocktwits calls are added in
FNI. The new client calls only configured gateway routes under
`/api/v1/market-data/narrative/source-events/*`.

## Verification Notes

- RED: `pytest tests/test_narrative_source_gateway_consumer.py -q` failed on
  missing `scripts.run_narrative_source_gateway_probe`.
- GREEN targeted: `pytest tests/test_narrative_source_gateway_consumer.py tests/test_market_data_gateway_contract.py -q`.
- Generated fixture probe report validates successful gateway-shaped rows.
- Generated live-status probe report records that `MARKET_DATA_GATEWAY_URL` is
  not configured in this FNI environment.
