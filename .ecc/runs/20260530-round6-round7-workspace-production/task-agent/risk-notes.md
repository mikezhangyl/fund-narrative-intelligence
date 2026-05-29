# Risk Notes

- Round 6 currently uses deterministic fixture payloads and local exports. Live
  workspace persistence, authenticated ownership, and scheduled refresh are
  future production concerns.
- Round 6 alerts are intentionally observational and should remain free of
  recommendation language.
- Round 7 AI summaries are deterministic assisted explanations in this slice;
  a future model-backed implementation must preserve citation, disable, and
  non-authoritative constraints.
- Feedback records are governance inputs only. Promotion or trusted-state
  mutation must stay behind the existing review/promotion gates.
