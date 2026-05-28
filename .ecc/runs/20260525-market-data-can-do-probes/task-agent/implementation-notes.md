# Implementation Notes

- Routed FNI local gateway sector and limit-up/down methods to the new
  provider-neutral gateway endpoints.
- Added gateway-only `fetch_etf_spot` and `fetch_news_briefs` source methods.
- Added runnable ETF spot, limit-up/down, and Tushare news smoke probe scripts.
- Enriched the existing sector scan report with data fetch mode, source, and
  degradation event metadata.
- Kept direct provider integrations out of FNI for these new Can-Do probes.
