from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SectorScanResult:
    status: str
    trade_date: str
    sector_count: int
    etf_count: int
    top_sectors: list[dict[str, Any]]
    top_etfs: list[dict[str, Any]]
    failures: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SectorScanner:
    def rank(
        self,
        *,
        sectors: list[dict[str, Any]],
        etfs: list[dict[str, Any]],
        limit: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            "top_sectors": _rank_rows(sectors, limit=limit),
            "top_etfs": _rank_rows(etfs, limit=limit),
        }


def execute_sector_scan(
    *,
    data_source: Any,
    trade_date: str,
    etf_symbols: list[str],
    scanner: SectorScanner | None = None,
    limit: int = 20,
) -> SectorScanResult:
    sectors: list[dict[str, Any]] = []
    etfs: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    try:
        sectors = data_source.fetch_sector_data(trade_date=trade_date)
        if not sectors:
            failures.append(
                {
                    "capability": "sector_concepts",
                    "provider_family": "akshare_or_gateway",
                    "reason": "sector endpoint returned no rows",
                }
            )
    except Exception as exc:
        failures.append(
            {
                "capability": "sector_concepts",
                "provider_family": "akshare_or_gateway",
                "reason": str(exc),
            }
        )
    try:
        etfs = data_source.fetch_etf_data(
            symbols=etf_symbols,
            start_date=trade_date,
            end_date=trade_date,
        )
    except Exception as exc:
        failures.append(
            {
                "capability": "etf_daily",
                "provider_family": "tushare_or_gateway",
                "reason": str(exc),
            }
        )

    ranked = (scanner or SectorScanner()).rank(
        sectors=sectors,
        etfs=etfs,
        limit=limit,
    )
    return SectorScanResult(
        status="partial" if failures else "completed",
        trade_date=trade_date,
        sector_count=len(sectors),
        etf_count=len(etfs),
        top_sectors=ranked["top_sectors"],
        top_etfs=ranked["top_etfs"],
        failures=tuple(failures),
    )


def _rank_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (_as_float(row.get("pct_change")), _as_float(row.get("amount"))),
        reverse=True,
    )[:limit]


def _as_float(value: Any) -> float:
    if value in (None, "", "--"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
