# Risk Notes

- CNINFO has no committed dependency in the default V1 report path.
- Live CNINFO behavior can change; tests rely on an injected fetcher and normalizer fixtures.
- The adapter currently normalizes metadata only; it does not download PDFs or convert announcements into scored evidence.
- CNINFO market-column inference is based on common A-share code prefixes and should be revisited if broader security types are added.
