from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from src.config import PROJECT_ROOT


@dataclass(frozen=True)
class ProviderRequestLogEntry:
    provider: str
    endpoint: str
    request_time: str
    response_time_ms: float
    status: str
    retry_count: int
    failure_reason: str | None = None
    row_count: int | None = None
    cache_hit: bool = False


class ProviderRequestLogger(Protocol):
    def log(self, entry: ProviderRequestLogEntry) -> None:
        raise NotImplementedError


class JsonlProviderRequestLogger:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or PROJECT_ROOT / "data" / "logs" / "provider_requests.jsonl")

    def log(self, entry: ProviderRequestLogEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


class InMemoryProviderRequestLogger:
    def __init__(self):
        self.entries: list[ProviderRequestLogEntry] = []

    def log(self, entry: ProviderRequestLogEntry) -> None:
        self.entries.append(entry)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
