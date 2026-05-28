from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from src.config import PROJECT_ROOT


class MarketDataCache(Protocol):
    def get(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        max_age_seconds: int | None = None,
    ) -> Any | None:
        raise NotImplementedError

    def set(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        payload: Any,
        created_at: datetime | None = None,
    ) -> None:
        raise NotImplementedError

    def get_or_set(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        loader: Callable[[], Any],
        max_age_seconds: int | None = None,
    ) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class CacheEntry:
    created_at: str
    payload: Any


class FileSystemMarketDataCache:
    def __init__(self, root_dir: Path | str | None = None):
        self.root_dir = Path(root_dir or PROJECT_ROOT / "data" / "cache")

    def get(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        max_age_seconds: int | None = None,
    ) -> Any | None:
        path = self._path(namespace=namespace, key_parts=key_parts)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(entry, dict) or "created_at" not in entry:
            return None
        if self._is_expired(str(entry["created_at"]), max_age_seconds):
            return None
        return entry.get("payload")

    def set(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        payload: Any,
        created_at: datetime | None = None,
    ) -> None:
        path = self._path(namespace=namespace, key_parts=key_parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = CacheEntry(
            created_at=(created_at or datetime.now(UTC)).isoformat(),
            payload=payload,
        )
        path.write_text(
            json.dumps(entry.__dict__, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def get_or_set(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        loader: Callable[[], Any],
        max_age_seconds: int | None = None,
    ) -> Any:
        cached = self.get(
            namespace=namespace,
            key_parts=key_parts,
            max_age_seconds=max_age_seconds,
        )
        if cached is not None:
            return cached
        payload = loader()
        self.set(namespace=namespace, key_parts=key_parts, payload=payload)
        return payload

    def _path(self, *, namespace: str, key_parts: dict[str, Any]) -> Path:
        safe_namespace = namespace.replace("/", "_").replace("..", "_")
        digest = hashlib.sha256(
            json.dumps(key_parts, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return self.root_dir / safe_namespace / f"{digest}.json"

    @staticmethod
    def _is_expired(created_at: str, max_age_seconds: int | None) -> bool:
        if max_age_seconds is None:
            return False
        try:
            created = datetime.fromisoformat(created_at)
        except ValueError:
            return True
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age = datetime.now(UTC) - created.astimezone(UTC)
        return age.total_seconds() > max_age_seconds


class NullMarketDataCache:
    def get(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        max_age_seconds: int | None = None,
    ) -> Any | None:
        return None

    def set(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        payload: Any,
        created_at: datetime | None = None,
    ) -> None:
        return None

    def get_or_set(
        self,
        *,
        namespace: str,
        key_parts: dict[str, Any],
        loader: Callable[[], Any],
        max_age_seconds: int | None = None,
    ) -> Any:
        return loader()
