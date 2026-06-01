## Risk Notes

- `source_quality_dashboard` can be `degraded` while the release checklist
  passes; this is intentional when source governance blocks or gateway probe
  degradation events are displayed.
- Live mode intentionally fails the acceptance checklist when gateway or
  Narrative Service URLs are missing. Demo mode remains deterministic and does
  not require live provider credentials.
- The product shell remains a static generated artifact surface, not a long
  running routed web server.
