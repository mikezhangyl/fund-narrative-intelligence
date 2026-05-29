# Narrative Radar Structured Source Mining - 2026-05-29

Canonical readable artifact:
`docs/product/narrative-radar-structured-source-mining-2026-05-29.html`

## Linear Scope

- `MIK-76`: Structured source mining into candidate narratives.

## Implemented Service Contract

Narrative Service now exposes:

```text
GET /api/v1/narratives/radar/mined-candidates
```

The endpoint mines candidate narratives from structured source events and
returns review-only candidate records. It does not promote trusted narratives.

`GET /api/v1/narratives/radar/signals` also consumes the mined candidates when
an eligible source event does not already carry an explicit
`candidate_narratives` payload.

## Mining Policy

The first deterministic mining policy is `structured_event_cooccurrence_v0`.

Allowed source types:

- `news`
- `announcement`
- `manual`

Excluded source types:

- `social_future`

Market confirmation is not used as narrative text. Browser automation, social
scraping, Snowball, Taoguba, X/Twitter, Reddit, proxy, and anti-bot work are not
included.

## Candidate Output

Each mined candidate includes:

- deterministic `candidate_narrative_id`
- candidate name from narrative hints or structured entities
- trust status `candidate_untrusted`
- human review status `candidate`
- source types and source origins
- stock codes
- extracted tickers, sectors, concepts, and keywords
- evidence references back to source event id, URL, title, time, type, and
  provider
- `promotion_effect=none`

## Verification

- RED:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_mining_creates_candidate_signals_from_structured_events services/stock-narrative-service/tests/test_http_service.py::test_radar_mining_excludes_reserved_social_sources_and_discloses_policy -q`
  failed on missing mined-candidates endpoint.
- GREEN:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 37 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`
  passed.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
