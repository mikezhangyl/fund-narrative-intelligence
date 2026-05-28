# Market Data Can-Do Roadmap

## Goal

Move the market-data work from validation-only into visible capability expansion.

The current priority is "Can Do" first: prove that FNI can fetch, normalize,
scan, and report useful market structure datasets through the consolidated data
layer and local gateway path. Do not spend the next slice chasing extreme
backend robustness once the basic gateway contract is working.

## Ownership Decision

New external data-source breakthroughs should happen in the local market-data
gateway first. FNI should define the consumer contract, write change-request
documents for the gateway project, and then implement scanners/reports against
the gateway API after the gateway exposes the data.

FNI should avoid adding another direct integration layer for Tushare, AkShare,
EastMoney, or news providers unless it is a small compatibility shim needed to
consume the gateway.

Current gateway request:

```text
/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/fni-can-do-market-data-capability-pack-change-request-2026-05-25.md
```

Status: implemented and accepted on 2026-05-25. The request should be read from
the gateway archive after cleanup:

```text
/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-can-do-market-data-capability-pack-change-request-2026-05-25.md
```

Flow/event gateway request:

```text
/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-flow-and-event-data-capability-pack-change-request-2026-05-26.md
```

Status: implemented and accepted by FNI on 2026-05-27.

Structural-data gateway request:

```text
/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-structure-mapping-data-capability-pack-change-request-2026-05-27.md
```

Status: implemented and accepted by FNI on 2026-05-27.

New stock-sector membership gateway request:

```text
/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-stock-sector-membership-data-capability-pack-change-request-2026-05-27.md
```

Status: implemented by gateway on 2026-05-27 and consumed by FNI. Current local
smoke can return structured degraded payloads when public upstreams are
unreachable, so FNI marks the dataset as `unstable` while keeping the endpoint
gateway-ready.

FNI runtime follow-up on 2026-05-27: the LaunchAgent-backed gateway on
`http://127.0.0.1:8700` was restarted with the current gateway checkout. The
route no longer returns 404. After the gateway timeout hardening, a bounded
live run with `MARKET_DATA_GATEWAY_TIMEOUT_SECONDS=20` and
`--sector-universe-limit 0` returned HTTP 200 through FNI in about 8 seconds
with no socket timeout. The result is still `missing` because no membership rows
were recovered, but FNI now captures the gateway degraded reason:
`REQUEST_TIMEOUT: Stock sector membership reverse index materialization timed
out.` Outputs:
`outputs/stock_sector_memberships_probe/2026-05-27-gateway-timeout-fix/` and
`outputs/holding_sector_exposure/2026-05-27-gateway-timeout-fix/`.

Fund profile/holdings gateway request:

```text
/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/archive/fni-fund-profile-and-holdings-data-capability-pack-change-request-2026-05-27.md
```

Status: implemented by gateway and accepted by FNI on 2026-05-27. FNI contract
endpoint IDs `gateway_fund_profile` and `gateway_fund_holdings` are now
`available`, and `fund_profile`/`fund_holdings` are `gateway_ready` datasets.
The FNI consumer path is `provider_mode=gateway` through
`LocalGatewayFundHoldingProvider`. Live conformance passed for fund `161725`,
and a gateway-backed fund report returned 10 fresh holdings with no FNI
degradation events. A lightweight revalidation probe now exists at
`scripts/run_fund_profile_holdings_probe.py`. Outputs:
`outputs/gateway_contract/2026-05-27-fund-profile-holdings.json` and
`outputs/gateway_fund_provider_smoke/2026-05-27-live-fund-holdings-v2/`;
probe output:
`outputs/fund_profile_holdings_probe/2026-05-27-live-gateway/`.

## Current Baseline

- Gateway normalized health is working at `MARKET_DATA_GATEWAY_URL`.
- FNI gateway request timeout is configurable with
  `MARKET_DATA_GATEWAY_TIMEOUT_SECONDS`; the default remains 10 seconds.
- FNI can use gateway async `daily-bars` jobs for large daily-bar batches.
- FNI can use gateway async `breadth-window` jobs for breadth scans.
- 500-symbol, 20-trading-day breadth-window validation completed through the
  gateway with 0 failed symbols and 9940 rows.
- Terminal breadth-window jobs no longer silently fall back to heavy daily-bars
  pulls inside FNI.
- Gateway provider-neutral sector, ETF spot, limit-up/down, and Tushare news
  brief endpoints are live and accepted by FNI conformance.
- Gateway CYQ chip distribution is live at `/api/v1/market-data/chips/cyq` and
  FNI conformance passed for the route on 2026-05-26. FNI now exposes the route
  through `LocalGatewayMarketDataProvider.fetch_cyq_chips` and the consolidated
  source layer. A runnable probe exists at `scripts/run_cyq_chips_probe.py`.
- Gateway northbound capital, main capital flow, ETF flow, and 龙虎榜 endpoints
  are live and accepted by FNI conformance/probes on 2026-05-27.
- Gateway sector constituents, ETF basic metadata, index constituents, margin
  summary/detail, and earnings calendar endpoints are live and accepted by FNI
  conformance/probes on 2026-05-27.
- Gateway fund profile and fund holdings endpoints are live and accepted by FNI
  conformance on 2026-05-27. FNI can now run fund reports with
  `--provider-mode gateway`; holdings date/source is taken from the disclosure
  rows rather than the profile metadata row.
- A repeated smoke check after the flow/event optimization showed the four
  flow/event routes are Can-Do stable enough to keep expanding. Treat them as
  auxiliary public-web-backed inputs until longer validation proves production
  stability.
- FNI has a Can-Do daily market structure report that combines breadth,
  sector heat, ETF heat, limit-up/down temperature, flow/event context, and
  Tushare news briefs:
  `scripts/run_daily_market_structure_report.py`.
- Daily market structure report now consumes the accepted flow/event routes and
  renders a funding/event context section: northbound net buy/sell direction,
  top main-capital-flow samples, top ETF-flow samples, dragon-tiger samples, and
  deterministic cross-links against structure-mapping rows.
- Daily market structure report now also consumes gateway CYQ chip distribution
  for a small cost-basis context section. This is a sample-level deterministic
  summary of cost-distribution buckets and peak bucket, not a trading signal.
- Daily market structure report consumes existing index daily and ETF daily
  surfaces for a light benchmark context section, so initial Tier 1 index OHLCV
  and ETF daily capability are visible in the reader-facing artifact.
- Daily market structure report now embeds the structure mapping summary as a
  temporary red-highlighted HTML section so the newly added content is easy to
  review. The section now renders deterministic cross-links such as theme/index,
  theme/margin, theme/event-calendar, and index/margin overlaps instead of only
  listing task or endpoint status.
- FNI has a Can-Do structure mapping report that combines sector constituents,
  ETF metadata, index constituents, margin summary/detail, and event calendar
  data:
  `scripts/run_structure_mapping_report.py`.
- New data requirement encountered: stock -> sector/concept reverse membership.
  FNI exposes this with a bounded `sector_universe_limit` control so Can-Do
  probes can stay small while the gateway reverse-index cache matures.
  Current gateway can answer sector -> constituents, but holding-level reports
  need the reverse lookup without FNI brute-forcing all boards.
- FNI now exposes stock-sector memberships through the local gateway provider,
  consolidated source layer, a runnable probe, and a thin Can-Do holding sector
  exposure report:
  `scripts/run_stock_sector_memberships_probe.py` and
  `scripts/run_holding_sector_exposure_report.py`.
- FNI runtime check after gateway timeout hardening on 2026-05-27 confirmed the
  deployed `http://127.0.0.1:8700` route returns bounded HTTP 200 degraded
  payloads instead of 404 or client socket timeouts. Current smoke output is
  under `outputs/stock_sector_memberships_probe/2026-05-27-gateway-timeout-fix/`
  and `outputs/holding_sector_exposure/2026-05-27-gateway-timeout-fix/`.
- Gateway fund profile and fund holdings routes are accepted and available.
  FNI can now select a local-gateway fund provider with `provider_mode=gateway`;
  this consumes `funds/profile` and `funds/holdings` and falls back to mock
  fixtures only when the gateway is unavailable or returns an invalid payload.
- FNI has a Can-Do fund holding exposure report:
  `scripts/run_fund_holding_exposure_report.py`. It starts from a fund code,
  pulls gateway holdings, aggregates industry exposure from holding rows,
  links holdings to reviewed local narrative mappings, and attempts
  stock-sector membership for board/concept exposure. A live 161725 run on
  2026-05-28 produced 10 holdings, one industry exposure, one reviewed narrative
  exposure (`N_BAIJIU_CONSUMPTION`), and a partial status because
  stock-sector membership still returned a degraded/missing result. Output:
  `outputs/fund_holding_exposure/2026-05-28-live-gateway/`.
- FNI has a Can-Do multi-fund exposure comparison report:
  `scripts/run_fund_exposure_comparison_report.py`. It compares gateway-backed
  fund holdings, concentration, holding overlap, common narrative exposure, and
  differentiating narrative exposure across multiple funds. A live run on
  2026-05-28 for `161725,515880,512760` produced usable holdings and narrative
  differences with `partial` status because stock-sector membership timed out
  through structured gateway degradation. Output:
  `outputs/fund_exposure_comparison/2026-05-28-live-gateway/`.
- Daily market structure report HTML is Chinese, includes metric/source
  hover details where practical, deterministic title-level news deduplication,
  and explicit connected-interface data-gap diagnostics.

## Can-Do Priorities

1. Keep breadth scanner usable as the first proof of market-structure scanning.
2. Use provider-neutral sector/concept capability from the gateway and keep the
   runnable FNI sector CLI/report.
3. Use ETF spot/daily capability from the gateway and keep the runnable FNI ETF
   ranking CLI/report.
4. Use provider-neutral limit-up/down statistics from the gateway and keep the
   daily market-temperature report.
5. Use gateway-owned index OHLCV and turnover-rate reads through the same source
   layer.
6. Use Tushare `news` through the gateway as the first preferred structured news
   source before considering direct news-site crawling.
7. Produce simple capability reports that answer: available, runnable, missing,
   degraded, and source.
8. Use gateway flow/event datasets: northbound capital, main capital flow, ETF
   flow, and 龙虎榜.
9. Add structure-mapping datasets through the gateway before adding more volatile
   public quote-style endpoints: sector constituents, ETF metadata, index
   constituents, margin data, and earnings/event calendar data.
10. Use gateway fund holdings in reader-facing exposure reports before asking
    the gateway for more sources: industry exposure, reviewed narrative exposure,
    and sector/concept exposure with explicit missing-data diagnostics.

## Useful Source Clues

- Market breadth reference: `https://sckd.dapanyuntu.com/` defines market
  breadth as the percentage of stocks whose close is above MA20 and updates
  after market close. Use this as a metric-definition reference and comparison
  target, not as a scraping source.
- Tushare news reference: `https://tushare.pro/news` / official `news` API
  documentation should be treated as the preferred V2 news entry point. The
  interface is source-based and time-window based, with fields such as
  `datetime`, `title`, `content`, and `channels`. It may require separate
  permission, so the first Can-Do step is a permission and smoke-test check.

## Backlog TODO: Robustness Optimization

These are important, but they should not block functional expansion:

- Improve cold-cache breadth-window throughput.
- Tune gateway request pacing and batch sizing for larger A-share windows.
- Add scheduled cache warming after market close.
- Expand coverage diagnostics for missing symbol-date pairs.
- Add richer retry policy controls for long-running gateway jobs.
- Add operational dashboards or observability integrations.
- Stabilize the provider-neutral sector concepts route. On 2026-05-27,
  `GET /api/v1/market-data/sectors/concepts` and the legacy AkShare-specific
  sector concepts route returned HTTP 500 while sector constituents still worked
  through EastMoney fallback.
- Tune ETF spot timeout/pacing. On 2026-05-27 it passed when validated alone
  with a longer timeout, but timed out during broad default conformance.
- Collect successful stock-sector membership rows after public upstream access
  recovers, then decide whether to raise `stock_sector_membership` from
  `unstable` to `available`.
- Stress test full-market, multi-year scans after the core capability matrix is
  broader.

## Later Design: News Briefs Analysis Layer

Current scope is deterministic news cleanup only:

- Normalize title text by removing whitespace and lowercasing.
- Group exact normalized-title matches.
- Keep the first row as the representative item.
- Merge channels and record duplicate count.
- Do not do semantic similarity, clustering, causal explanation, or board/ETF
  attribution in the report renderer.

Later `news briefs` analysis should be a separate design, likely with an AI
agent or model-backed analyst layer. That design should consume structured news
briefs plus market structure outputs and emit reviewable JSON with event
clusters, candidate related sectors/narratives, confidence, source citations,
and uncertainty. The HTML report may render that output only after the analysis
contract is explicit and testable.

## Near-Term Acceptance

- A user can run one command each for breadth, sector, ETF, and limit-up/down
  probes.
- A user can run one news-source permission/smoke probe for Tushare `news`.
- Each formal report command emits JSON and HTML reports under `outputs/`;
  Markdown is auxiliary only and must not be the canonical reading surface.
- Each report identifies `data_fetch_mode`, provider/source, row counts,
  failures, and degradation events.
- Structure mapping report can run against the gateway and emit Chinese JSON/HTML
  showing sector constituents, ETF metadata, index constituents, margin context,
  and event calendar rows.
- Fund holding exposure report can run against the gateway and emit Chinese
  JSON/HTML showing holdings, industry exposure, reviewed narrative exposure,
  sector/concept exposure when available, and explicit data gaps when
  stock-sector membership is degraded.
- Failures are explicit and actionable, but perfect resilience is not required
  in this phase.

## Non-Goals For This Slice

- No trading strategy.
- No AI prediction.
- No browser scraping.
- No proxy or anti-detect system.
- No real-time websocket infrastructure.
- No attempt to make the gateway production-perfect before adding new data
  capabilities.
