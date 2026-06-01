# Risk Notes

- The digest is only as fresh as the gateway probe/source-event artifact used as input.
- Entity resolution is contract-first and deterministic for current event fields; richer provider aliases may require an expanded gateway payload.
- The crawler adapter contract is documented and test-covered here, but provider crawling behavior must be enforced in Gateway.
- The generated HTML is a readable operational surface, not a trading recommendation surface.
