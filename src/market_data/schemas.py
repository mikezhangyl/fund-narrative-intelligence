from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    trade_date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    pre_close: float | None
    volume: float | None
    amount: float | None
    turnover_rate: float | None
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SectorSnapshot:
    sector_code: str | None
    sector_name: str
    trade_date: str | None
    pct_change: float | None
    turnover_rate: float | None
    amount: float | None
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    endpoint: str
    ok: bool
    latency_ms: float
    checked_at: str
    row_count: int | None = None
    schema_fingerprint: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
