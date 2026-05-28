from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PostgresConfig:
    dsn_env_var: str = "DATABASE_URL"
    connect_timeout_seconds: int = 10


class PostgresStoreUnavailable(RuntimeError):
    pass


class PostgresStore:
    def __init__(self, config: PostgresConfig | None = None):
        self.config = config or PostgresConfig()

    def connect(self):
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise PostgresStoreUnavailable(
                "psycopg is not installed; use FileSystemMarketDataCache or install "
                "a PostgreSQL driver for production persistence"
            ) from exc
        dsn = os.getenv(self.config.dsn_env_var)
        if not dsn:
            raise PostgresStoreUnavailable(
                f"{self.config.dsn_env_var} is not configured"
            )
        return psycopg.connect(
            dsn,
            connect_timeout=self.config.connect_timeout_seconds,
        )
