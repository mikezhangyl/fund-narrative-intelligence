# Information Source Diversification

## Goal

Shift the next project slices away from wrapper-first provider expansion and
toward source-first intelligence expansion for A-share and domestic-market
funds.

The system should prefer more independent evidence sources, stronger
cross-checking, and explicit uncertainty over silent fallback to mock-backed
outputs.

## Why This Slice Exists

- Current optional provider work improved routing, but provider count alone
  does not guarantee more independent information.
- Many "free" adapters for domestic equities still rely on the same upstream
  sources such as Eastmoney, so swapping wrappers does not meaningfully
  diversify evidence.
- The product goal is narrative intelligence, not only quote retrieval. Higher
  evidence density and cross-source consistency matter more than adding another
  near-duplicate market-data wrapper.
- Mock-backed intelligence should become a last-resort safety net, not the
  normal answer when real-source coverage is thin.

## Scope

- Prioritize independent source expansion for:
  - news evidence
  - announcements and announcement-derived evidence
  - provider-derived evidence and signals
- Define the operating rule that uncertain or conflicting real information
  should surface as `partial`, `conflicting`, or `low-confidence` rather than
  falling back to mock by default.
- Reserve large-model reasoning for semantic judgment tasks such as:
  - event clustering
  - narrative classification
  - conflict detection
  - evidence-strength comparison
- Keep the near-term focus on A-share and domestic funds.

## Out Of Scope

- Paid Hong Kong data expansion
- Blindly replacing every source with AKShare or Tushare wrappers
- LLM-generated raw facts or fabricated numeric data
- Removing deterministic mock fixtures from the repo before real-source paths
  are proven

## Operating Principles

1. Prefer independent information sources over multiple wrappers of the same
   upstream website.
2. Expand evidence-bearing sources before expanding low-signal numeric sources.
3. Use provider contracts to preserve provenance, source URLs, and degradation
   reasons at every layer.
4. When real sources disagree or degrade, disclose uncertainty explicitly
   instead of silently substituting mock evidence.
5. Use LLMs in the semantic judgment layer, not the raw fetch layer.

## Proposed Order

1. Expand `news_evidence` with additional independent domestic news sources.
2. Strengthen `announcements` and `announcement_evidence` so regulatory and
   issuer disclosures remain the highest-confidence narrative inputs.
3. Increase provider-derived evidence and signal coverage so the pipeline can
   rely less on fixture-backed intelligence layers.
4. Add cross-source consistency and conflict reporting before adding new
   wrapper-only quote or financial providers.
5. Introduce targeted LLM semantic judgment only after source provenance and
   multi-source evidence density are sufficient.

## Acceptance

- Project memory and interface inventory clearly state that source
  diversification is preferred over wrapper count.
- New source work defaults to real-source `partial` or `conflicting`
  disclosure, not mock substitution, unless no usable real path exists.
- Future news/evidence slices document whether a new provider adds an
  independent source or only a new wrapper over an existing source.
- LLM-assisted semantic classification work, when introduced, is explicitly
  positioned after source fetch and before scoring/report interpretation.

## First Concrete Targets

- Add at least one more independent domestic news source to
  `multi-source-news`.
- Improve announcement-derived evidence density before expanding paid or
  experimental numerical providers.
- Start replacing fixture-backed evidence and signals with provider-derived
  equivalents where provenance is already strong.
