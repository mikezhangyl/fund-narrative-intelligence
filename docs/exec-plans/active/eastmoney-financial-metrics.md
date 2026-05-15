# Eastmoney Financial Metrics

## Goal

Add an optional real financial-metrics layer so earnings score can consume
provider financial indicators instead of relying only on fixture or announcement
signals.

## Scope

- Add an Eastmoney F10 financial metrics provider with injectable fetcher.
- Emit `financial_metrics` in raw/scoring artifacts when explicitly requested.
- Add a non-mock `financial_metrics` provider-foundation layer.
- Derive deterministic earnings signals from revenue/profit growth metrics.
- Extend reviewed-mapping enriched acceptance to exercise the layer.

## Non-Goals

- No historical financial statement warehouse.
- No pandas/AKShare/Tushare dependency in this slice.
- No LLM interpretation of financial statements.

## Acceptance

- Provider tests cover successful parsing and provider failure degradation.
- Pipeline tests show provider metrics produce earnings-derived signals.
- Reviewed-mapping enriched acceptance passes with `financial_metrics=eastmoney`.
- Mock/fallback disclosure remains visible in baseline paths.
