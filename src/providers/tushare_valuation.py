from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import local_env
from src.providers.security_market import tushare_a_share_ts_code
from src.providers.tushare_common import (
    TUSHARE_API_URL,
    TushareFetcher,
    as_float,
    get_tushare_api_url,
    iso_date,
    latest_row,
    query_tushare_rows,
    stock_basic_metadata,
)
from src.validation import validate_valuation_snapshot_payload

TUSHARE_VALUATION_PROVIDER = "tushare-valuation"
TUSHARE_VALUATION_VERSION = "tushare-valuation-v1"
TUSHARE_SOURCE_URL = TUSHARE_API_URL

_DAILY_BASIC_FIELDS = ",".join(
    [
        "ts_code",
        "trade_date",
        "close",
        "turnover_rate",
        "pe_ttm",
        "pb",
        "total_mv",
        "circ_mv",
    ]
)
_DAILY_FIELDS = ",".join(
    [
        "ts_code",
        "trade_date",
        "pre_close",
        "pct_chg",
    ]
)


class TushareValuationProvider:
    provider_name = TUSHARE_VALUATION_PROVIDER
    provider_version = TUSHARE_VALUATION_VERSION
    source_url = TUSHARE_SOURCE_URL

    def __init__(
        self,
        token: str | None = None,
        fetcher: TushareFetcher | None = None,
    ):
        self.token = (
            token if token is not None else local_env.get_config_value("TUSHARE_TOKEN")
        )
        self.fetcher = fetcher
        self.source_url = get_tushare_api_url()
        self.degradation_events: list[dict[str, str]] = []

    def get_valuation_snapshots(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not self.token:
            self.degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider": self.provider_name,
                    "reason": "TUSHARE_TOKEN is not configured",
                }
            )
            return _unavailable_payload(stock_codes=stock_codes, retrieved_at=retrieved_at)

        valuations: list[dict[str, Any]] = []
        failed_stock_codes: list[str] = []
        for stock_code in stock_codes:
            ts_code = tushare_a_share_ts_code(stock_code)
            if ts_code is None:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unsupported_market",
                        "provider": self.provider_name,
                        "reason": (
                            "Tushare valuation currently supports A-share stock codes only: "
                            f"{stock_code}"
                        ),
                    }
                )
                continue
            try:
                valuations.append(
                    _build_valuation_snapshot(
                        ts_code=ts_code,
                        token=self.token,
                        fetcher=self.fetcher,
                        retrieved_at=retrieved_at,
                    )
                )
            except Exception as exc:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider": self.provider_name,
                        "reason": f"Tushare valuation fetch failed for {stock_code}: {exc}",
                    }
                )

        payload = {
            "version": "valuation-snapshot-v1",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(valuations, failed_stock_codes),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "valuation_basis": "provider_valuation_metrics",
            "valuations": valuations,
            "missing_stock_codes": sorted(set(failed_stock_codes)),
        }
        validate_valuation_snapshot_payload(payload)
        return payload


def _build_valuation_snapshot(
    *,
    ts_code: str,
    token: str,
    fetcher: TushareFetcher | None,
    retrieved_at: str,
) -> dict[str, Any]:
    daily_basic_rows = query_tushare_rows(
        token=token,
        api_name="daily_basic",
        params={"ts_code": ts_code},
        fields=_DAILY_BASIC_FIELDS,
        fetcher=fetcher,
    )
    daily_rows = query_tushare_rows(
        token=token,
        api_name="daily",
        params={"ts_code": ts_code},
        fields=_DAILY_FIELDS,
        fetcher=fetcher,
    )
    daily_basic_row = latest_row(daily_basic_rows, date_fields=("trade_date",))
    daily_row = _best_matching_daily_row(
        daily_rows=daily_rows,
        daily_basic_row=daily_basic_row,
    )
    if daily_basic_row is None and daily_row is None:
        raise ValueError(f"No Tushare valuation rows returned for {ts_code}")

    stock_code = ts_code.split(".")[0]
    metadata = stock_basic_metadata(
        ts_code=ts_code,
        token=token,
        fetcher=fetcher,
    )
    pe_ttm = as_float((daily_basic_row or {}).get("pe_ttm"))
    pb = as_float((daily_basic_row or {}).get("pb"))
    return {
        "stock_code": stock_code,
        "stock_name": str(metadata.get("stock_name") or stock_code),
        "latest_price": as_float((daily_basic_row or {}).get("close")),
        "previous_close": as_float((daily_row or {}).get("pre_close")),
        "price_change_percent": as_float((daily_row or {}).get("pct_chg")),
        "valuation_pressure": _valuation_pressure(pe_ttm=pe_ttm, pb=pb),
        "source": "provider_valuation_metrics",
        "source_provider": TUSHARE_VALUATION_PROVIDER,
        "source_url": get_tushare_api_url(),
        "retrieved_at": retrieved_at,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "market_cap": as_float((daily_basic_row or {}).get("total_mv")),
        "float_market_cap": as_float((daily_basic_row or {}).get("circ_mv")),
        "turnover_rate": as_float((daily_basic_row or {}).get("turnover_rate")),
        "report_date": iso_date((daily_basic_row or {}).get("trade_date")),
    }


def _best_matching_daily_row(
    *,
    daily_rows: list[dict[str, Any]],
    daily_basic_row: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not daily_rows:
        return None
    if daily_basic_row is None:
        return latest_row(daily_rows, date_fields=("trade_date",))
    target_trade_date = str(daily_basic_row.get("trade_date") or "")
    for row in daily_rows:
        if str(row.get("trade_date") or "") == target_trade_date:
            return row
    return latest_row(daily_rows, date_fields=("trade_date",))


def _valuation_pressure(pe_ttm: float | None, pb: float | None) -> str:
    if pe_ttm is None and pb is None:
        return "unknown"
    if (pe_ttm is not None and pe_ttm >= 40) or (pb is not None and pb >= 8):
        return "elevated"
    if (pe_ttm is not None and 0 < pe_ttm <= 12) or (pb is not None and 0 < pb <= 1.5):
        return "discounted"
    return "neutral"


def _data_quality(
    valuations: list[dict[str, Any]],
    missing_stock_codes: list[str],
) -> str:
    if not valuations:
        return "unavailable"
    if missing_stock_codes:
        return "partial"
    return "fresh"


def _unavailable_payload(
    *,
    stock_codes: list[str],
    retrieved_at: str,
) -> dict[str, Any]:
    payload = {
        "version": "valuation-snapshot-v1",
        "provider_name": TUSHARE_VALUATION_PROVIDER,
        "provider_version": TUSHARE_VALUATION_VERSION,
        "data_quality": "unavailable",
        "source_url": get_tushare_api_url(),
        "retrieved_at": retrieved_at,
        "valuation_basis": "provider_valuation_metrics",
        "valuations": [],
        "missing_stock_codes": sorted(set(str(code) for code in stock_codes)),
    }
    validate_valuation_snapshot_payload(payload)
    return payload
