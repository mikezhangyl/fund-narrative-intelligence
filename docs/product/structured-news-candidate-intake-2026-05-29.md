# Structured News Candidate Intake - 2026-05-29

## Scope

This slice implements the Round 2 MIK-55 workflow for turning structured
gateway/Tushare news briefs into candidate narrative intake events.

The workflow consumes provider-neutral news brief rows and converts selected
items into `source-event-schema-v1` events with `source_type=news`. It does not
crawl news websites, does not integrate social sources, and does not promote any
candidate to a reviewed or trusted narrative store.

## Entry Point

```bash
uv run python scripts/run_news_candidate_intake.py \
  --output-dir outputs/news_candidate_intake/2026-05-29-mik-55-fixture
```

By default, the script reads
`data/fixtures/news_briefs_for_candidate_intake.v1.json`. For live gateway
smoke use, pass `--live --start-datetime ... --end-datetime ...`; live mode
uses `ConsolidatedMarketDataSource.fetch_news_briefs`.

## Contract

- Input contract: gateway/Tushare news briefs.
- Conversion contract: `src.scanners.news_candidate_intake.news_briefs_to_source_events`.
- Source event schema: `source-event-schema-v1`.
- Default provider: `gateway_news_briefs`.
- Default raw provider/source: `tushare` / `sina`.
- External access policy: gateway change request first; direct crawling is
  disabled.
- Trust policy: all generated events, candidate narratives, evidence
  reinforcement rows, and mapping review items remain `candidate_untrusted`.

## Fixture Result

The fixture acceptance run generated:

- JSON: `outputs/news_candidate_intake/2026-05-29-mik-55-fixture/news_candidate_intake_report.json`
- HTML: `outputs/news_candidate_intake/2026-05-29-mik-55-fixture/news_candidate_intake_report.html`

Fixture summary:

- News events: 2
- New candidate narratives: 1 (`机器人执行器`)
- Existing narrative reinforcements: 1 (`N_BAIJIU_CONSUMPTION`)
- Candidate stock mappings: 3
- Review queue items: 4

The output includes `news_source_trace`, which shows the raw news provider,
source channel, source URL, event ID, candidate target, and trust state for each
created or reinforced candidate.
