# Risk Notes

- Reserved market, valuation, announcement, and news providers intentionally return empty mock payloads.
- Real providers still need source-specific validation and rate-limit handling when implemented.
- `MockDataProvider` remains the compatibility facade for the orchestrator; future work can split the orchestrator only when real layer providers require it.
