# Round 13 Narrative Source Deep Mining Plan - 2026-06-01

## Product Goal

Narrative Service must become a source-backed discovery system for fresh market
narratives. The user should be able to ask: "What new stories are emerging
recently or today?" and receive candidate narratives with evidence, source
quality labels, freshness/trend state, and affected entities.

This round is about source depth and trust. It is not a trading strategy, price
prediction engine, or unbounded scraping project.

## Core Product Position

Narratives should come from a source pyramid:

1. Trusted facts: official disclosures, exchange/regulator releases, company IR,
   policy documents, earnings materials, and audited/public filings.
2. Timely professional news: paid or permissioned news/data feeds such as
   Tushare news, Wind/Choice/iFinD, LSEG/Reuters, RavenPack, AlphaSense,
   Benzinga, Finnhub, or equivalent providers.
3. Research context: industry media, public financial portals, association
   releases, sell-side/research summaries where licensed, and public web pages.
4. Heat/candidate signals: EastMoney Guba, Xueqiu, Stocktwits, Reddit, X,
   Weibo, and similar community/social sources.

Only tiers 1 and 2 can directly support trusted narrative facts. Tier 3 can
support context after source quality checks. Tier 4 is discovery/heat only until
corroborated by trusted evidence.

## Source Decision Matrix

| Source group | Examples | Role | First status | Owner boundary | Key risk |
| --- | --- | --- | --- | --- | --- |
| Existing structured news | Tushare `news` | Timely news | Can-Do / permission smoke | Gateway source, Narrative consumer | Permission and coverage |
| China paid terminals | Wind, Choice, iFinD | China news/data/research | Paid Trial | Gateway/source adapter | Contract cost, API entitlement |
| Global professional news | LSEG/Reuters, Dow Jones, Bloomberg, FactSet, S&P | Global breaking news | Paid Trial | Paid-provider adapter | Cost and redistribution rights |
| News analytics | RavenPack / Bigdata.com, AlphaSense | Entity/event/sentiment/research search | Paid Trial | Narrative source adapter | Vendor lock-in, taxonomy fit |
| Developer news APIs | Benzinga, Finnhub, GDELT | Fast experiment / global coverage | Trial / Can-Do | Gateway or Narrative adapter | Coverage and full-text limits |
| Official disclosures | CNINFO, SSE/SZSE, HKEX, SEC EDGAR, company IR | Trusted facts | Can-Do / Crawl Pilot | Gateway for market data, Narrative for source events | Entity mapping and document parsing |
| Policy/regulator/industry | NDRC, MIIT, CSRC, ministries, associations | Trusted macro/industry facts | Crawl Pilot | Narrative source adapter | Page variance, update frequency |
| Financial portals/industry media | EastMoney, Sina Finance, Securities Times, vertical tech/industry media | Context and early signals | Crawl Pilot | Narrative source adapter | Copyright, robots/TOS, anti-bot |
| Community/social | EastMoney Guba, Xueqiu, Stocktwits, Reddit, X, Weibo | Heat and candidate discovery | Controlled Pilot | Narrative heat adapter | Terms, rate limits, misinformation |

## Paid Source Strategy

Paid sources are worth considering when they reduce fragility or provide
licensed metadata we cannot reliably reconstruct ourselves.

China-first recommendation:

- Evaluate Wind, Choice, and iFinD as institutional options.
- Keep Tushare news as the low-friction first smoke because FNI/gateway already
  have Tushare operational context.
- Treat paid terminal data as a contract/API question, not a scraping target.

Global/news-analytics recommendation:

- Evaluate LSEG/Reuters when low-latency professional financial news and
  redistribution terms matter.
- Evaluate RavenPack/Bigdata.com when the value is entity/event/sentiment and
  novelty metadata rather than raw article collection.
- Evaluate AlphaSense when the value is market-intelligence search over
  transcripts, filings, broker/research, and news.
- Use Benzinga/Finnhub/GDELT as cheaper or faster integration candidates, but
  verify full-text availability, latency, rate limits, historical depth, and
  redistribution rights before relying on them.

## Self-Mining / Crawling Strategy

We should self-mine public sources where the content is lawful to access,
operationally stable, and valuable enough to normalize.

Allowed pilot pattern:

- Use public pages, RSS, sitemaps, official APIs, and static article pages.
- Respect robots/TOS and per-domain pacing.
- Cache raw fetch metadata and content hash.
- Store source URL, published time, fetched time, parser version, and failure
  reason.
- Parse into source events first; never promote crawler output directly into a
  trusted narrative without evidence review or source scoring.

Explicitly out of scope:

- CAPTCHA bypass.
- Stealth browser or anti-detect browser farms.
- Residential proxy evasion.
- Scraping login-only or paywalled content without permission.
- Treating copied community posts as facts.

## Architecture Contract

Narrative source ingestion should normalize into:

```text
SourceEvent
  -> NarrativeFact
  -> CandidateNarrative
  -> EvidencePack
  -> Radar / Digest / Review Workspace
```

Required source event fields:

- `source_id`
- `provider`
- `source_type`
- `source_url`
- `license_scope`
- `published_at`
- `fetched_at`
- `raw_hash`
- `title`
- `excerpt`
- `language`
- `entities`
- `topics`
- `event_type`
- `extraction_method`
- `source_trust_tier`
- `confidence`
- `freshness_bucket`
- `anti_bot_risk`
- `evidence_ids`
- `degradation_warnings`

Required source quality fields:

- availability
- latency/freshness
- completeness
- schema stability
- entity metadata quality
- license clarity
- anti-bot risk
- retry recoverability
- operational cost
- contradiction/dispute rate

## Today's Narrative Digest

The user-facing first output should be a "today/recent narrative digest":

- New narratives: appeared for the first time in the current window.
- Accelerating narratives: mention/source count or source quality rose sharply.
- Persistent narratives: still active across multiple windows.
- Cooling narratives: previously active but declining.
- Disputed narratives: evidence conflicts or source trust is weak.

Each digest item must show:

- narrative title
- why it appeared
- affected stocks/sectors/funds/entities
- evidence links
- source quality labels
- trend direction
- freshness
- trust state
- missing evidence or caveats

## PM Requirements Created In Linear

- `MIK-221`: PM parent requirement pack.
- `MIK-223`: Source acquisition decision matrix.
- `MIK-224`: Licensed news and market-intelligence provider evaluation pack.
- `MIK-225`: Official disclosure and regulator source intake plan.
- `MIK-226`: Public web and industry media crawler pilot plan.
- `MIK-227`: Community and social heat source pilot plan.
- `MIK-228`: Today's narrative monitoring digest requirement.
- `MIK-239`: Tushare news permission and live data smoke.
- `MIK-240`: China paid provider trial checklist for iFinD, Choice, and Wind.
- `MIK-241`: Global paid news analytics trial checklist.
- `MIK-242`: China community and social source access investigation.

## Architecture Requirements Created In Linear

- `MIK-222`: Architect parent requirement pack.
- `MIK-229`: Source acquisition governance and compliance model.
- `MIK-230`: Narrative source-event and fact schema v2.
- `MIK-231`: Source reliability, licensing, and anti-bot risk scoring.
- `MIK-232`: Crawler adapter contract and robots/rate-limit policy.
- `MIK-233`: Fresh narrative digest pipeline contract.
- `MIK-234`: Entity resolution and deduplication contract.
- `MIK-243`: Narrative evidence storage model feasibility.
- `MIK-244`: Lightweight lakehouse user scenarios and data classes.
- `MIK-245`: Lightweight narrative lakehouse architecture spec.
- `MIK-246`: Narrative storage MVP schema and repository contract.
- `MIK-247`: Local raw zone layout and blob manifest MVP.
- `MIK-248`: Search and vector index deferral plan.
- `MIK-249`: Docker local lakehouse runtime profile.

## Dev-Ready Source Slices Created In Linear

These are directions where PM has verified live sample data can be fetched.
They are not production stability certifications.

- `MIK-235`: SEC EDGAR official filing source adapter MVP.
- `MIK-236`: CNINFO official disclosure event classifier expansion.
- `MIK-237`: Public news context cleanup and source-quality labels.
- `MIK-238`: Stocktwits heat-signal controlled pilot.

Evidence summary:

- SEC EDGAR submissions API returned Apple filing metadata with 1000 recent
  filing rows.
- CNINFO returned two recent `000001` announcements for a 30-day window.
- Google News RSS returned 100 results for an A-share semiconductor query.
- Sina Finance returned rows, but the parser includes navigation noise that must
  be cleaned.
- Stocktwits public symbol stream returned five AAPL messages.
- GDELT returned HTTP 429 and should not be handed to Developer until strict
  queue/cache pacing is designed.

## Storage Thesis

Narrative ingestion produces raw files, provider payloads, article snippets,
sentence-level evidence, entity mentions, candidate narratives, evidence packs,
and review decisions. The initial storage thesis is documented in
`docs/product/narrative-evidence-storage-model-initial-thesis-2026-06-01.md`.
The concrete lightweight lakehouse architecture is documented in
`docs/product/lightweight-narrative-lakehouse-architecture-2026-06-01.md`.

Short version:

- relational tables are the source of truth for source registry, fetch runs,
  normalized source events, evidence spans, entities, narratives, evidence
  packs, and review ledger;
- Docker Postgres should be the local integration-mode relational store, while
  SQLite remains useful for fast tests and offline fixture mode;
- Docker MinIO or an equivalent object-store profile should back the local
  Bronze raw zone, while temporary filesystem paths remain useful for tests;
- raw payloads and files are persisted only when retention and license rules
  allow it;
- full-text search and embeddings are derived indexes, not the source of truth;
- paid/news/social content should default to metadata and permitted excerpts
  unless a license explicitly allows full-text retention.

## Recommended Build Order

1. `MIK-229` + `MIK-231`: source governance and scoring first, so the system
   does not accept untrusted source sprawl.
2. `MIK-223`: source acquisition matrix, using the governance fields.
3. `MIK-230` + `MIK-234`: source event schema and entity/dedupe contract.
4. `MIK-225`: official disclosures and regulator intake.
5. `MIK-224`: paid provider trial pack.
6. `MIK-233` + `MIK-228`: today's narrative digest contract and product
   requirement.
7. `MIK-226` / `MIK-227`: crawler and community pilots after risk controls.

## References Checked

- Tushare news API documentation: https://www.tushare.pro/document/41?doc_id=143
- SEC EDGAR APIs: https://www.sec.gov/edgar/sec-api-documentation
- CNINFO: https://www.cninfo.com.cn/
- iFinD data API FAQ: https://ftwc.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/faq.html
- Choice data terminal/API surface: https://choice.eastmoney.com/
- LSEG News API / Reuters News: https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/news-API
- RavenPack news analytics: https://marketing-prod.ravenpack.com/products/edge/data/news-analytics
- Benzinga APIs: https://www.benzinga.com/apis/
- GDELT Cloud API: https://docs.gdeltcloud.com/api-reference
- Reddit API documentation: https://www.reddit.com/dev/api/
- X API rate limits: https://docs.x.com/x-api/fundamentals/rate-limits
