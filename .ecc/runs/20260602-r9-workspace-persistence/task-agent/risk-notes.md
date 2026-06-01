# Risk Notes

- This slice implements JSON-file persistence and migration contracts; SQLite/Postgres adapters remain future work behind the repository interface.
- The local CLI is the current save path. A richer interactive UI can call the same repository contract later.
- Secret detection is key-based and intentionally conservative; future preference work can add deeper value redaction rules.
