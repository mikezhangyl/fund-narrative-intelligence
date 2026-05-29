# Implementation Notes

Round 6 adds `portfolio-narrative-workspace-v1` as an FNI-owned workspace
aggregation surface. It keeps Gateway/Narrative Service boundaries explicit,
validates watchlists, builds exposure snapshots and comparisons, emits
observational alerts, and connects heating radar narratives to affected
watchlists and holdings.

Round 7 adds `production-readiness-assisted-intelligence-v1` as an FNI-owned
production and governance surface. It reports service health, runbooks,
freshness/SLA status, citation-backed AI explanations, and feedback records
that create review inputs without mutating trusted state.

Both surfaces follow the project report policy: JSON is machine-readable and
Chinese HTML is the canonical readable artifact.
