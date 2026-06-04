# Open-Source-First Narrative Data Strategy - 2026-06-04

Canonical readable artifact:
`docs/product/open-source-first-narrative-data-strategy-2026-06-04.html`

## Decision

Narrative source expansion should move from paid-provider-first evaluation to
free/open/public-source-first capability building.

This does not change the service boundary:

- `stock-data-gateway` owns external source acquisition, crawling, official API
  calls, credentials if any, request pacing, cache, robots/TOS metadata, raw
  payload policy, source-event normalization, and provider-neutral endpoints.
- FNI owns product requirements, consumer contracts, conformance probes,
  source-quality display, digest/report surfaces, and review workflows.

## Why Change Direction

The near-term goal is not to replicate a professional news terminal. The goal is
to build a reliable narrative fact and signal pipeline that can answer:

> What new market stories are emerging, what evidence supports them, and how
> trustworthy are the sources?

Free/open/public sources are enough for this Can-Do phase if we separate source
trust correctly:

- official sources can become trusted facts;
- open web/news can become context or candidate evidence;
- social/community sources can only become heat signals;
- paid providers remain optional later, not the current dependency.

## Source Priority

| Priority | Source class | Examples | Owner | Trust role |
| --- | --- | --- | --- | --- |
| P0 | Official disclosures and filings | SEC EDGAR, CNINFO, SSE/SZSE disclosure pages, HKEX where practical | Gateway | Trusted fact metadata and document reference |
| P0 | Policy/regulator/industry official pages | CSRC, exchanges, ministries, industry associations | Gateway | Trusted macro/industry fact |
| P1 | Open news/RSS/index sources | GDELT, Google News RSS-style feeds, media RSS, public sitemaps | Gateway | Context/candidate only |
| P1 | Public industry media | static article pages and low-risk public pages | Gateway | Research context after robots/TOS review |
| P2 | Community/social heat | Stocktwits, public forum pages, community pages where allowed | Gateway | Heat signal only |
| Later | Paid terminals/news analytics | Wind, Choice, iFinD, Reuters, RavenPack, AlphaSense | PM/vendor evaluation only | Optional future fallback |

## Non-Goals

- no paid provider integration in the current source-expansion milestone;
- no CAPTCHA bypass;
- no stealth browser or anti-detect infrastructure;
- no residential proxy evasion;
- no login-only or paywalled scraping without permission;
- no social/community post promoted as trusted fact;
- no FNI direct source adapters for SEC/CNINFO/news/social.

## Gateway User Stories Created In Linear

New shared Linear milestone:

- `M20 - Open Narrative Source Gateway Capability`

Gateway-owned stories:

- `[GATEWAY][P0][M20] Open source crawl governance runtime`
- `[GATEWAY][P0][M20] SEC EDGAR official filing source events`
- `[GATEWAY][P0][M20] China official disclosure source events`
- `[GATEWAY][P0][M20] Policy/regulator/industry official source events`
- `[GATEWAY][P1][M20] Open news/RSS context source events`
- `[GATEWAY][P1][M20] Public industry media crawler pilot`
- `[GATEWAY][P2][M20] Community/social heat controlled pilot`

FNI-owned follow-up stories:

- `[FNI][P0][M20] Source quality dashboard coverage for gateway source kinds`
- `[FNI][P0][M20] Fresh narrative digest from gateway open-source events`
- `[FNI][P1][M20] Live source conformance lane for open-source gateway routes`

## Acceptance Gate

The milestone is accepted when:

- gateway exposes provider-neutral source-event routes for at least one official
  source and one context/heat source;
- every source event includes source URL, published/fetched time, raw hash or
  metadata hash, license/retention policy, trust tier, source quality label,
  and degradation events;
- FNI consumes those routes only through gateway contracts;
- FNI source-quality dashboard shows coverage for every gateway source kind;
- fresh narrative digest can show new/accelerating/cooling candidates with
  evidence links and trust labels;
- deterministic local release remains credential-free, while live source checks
  are explicit operator actions.

## Product Position

This strategy optimizes for learning and reliable Can-Do capability before
vendor spend. Paid sources are not rejected permanently; they are no longer the
default path for the current phase.
