# Risk Notes

- The quality formula is deterministic v1 and intentionally simple. It should be treated as governance metadata, not a statistical model.
- Provider reliability uses recorded source metadata only; it does not call gateway/provider services during scoring.
- Source metadata filtering is key-based and strips secret/token/key/password/credential-like fields. Future nested metadata may need recursive redaction if nested source payloads are admitted.
- The default CLI acceptance data has limited fixture breadth; HTTP tests contain deterministic strong, weak, stale, and contradicted cases.
