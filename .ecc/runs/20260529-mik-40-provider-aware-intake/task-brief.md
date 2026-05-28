# Task Brief

## Linear

- Issue: MIK-40
- Title: [P1][PM] News and announcement candidate intake via gateway/service contracts
- Milestone: M2 - Reviewable Narrative Workflow

## Acceptance Focus

- Support provider-aware intake for `news`, `announcement`, `manual`, and `social_future`.
- Prefer gateway/Tushare structured feeds before public news-site crawling.
- Preserve provider/source metadata, permission status, and degradation state.
- Keep all intake outputs `candidate_untrusted`.
- Allow existing narratives to receive evidence reinforcement without trusted promotion.

## TDD Evidence

Red tests were added for provider-aware source metadata, evidence reinforcement without promotion, and contract-level intake policy before implementation.
