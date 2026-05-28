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
    quarter_report_type,
    query_tushare_rows,
    stock_basic_metadata,
)
from src.validation import validate_financial_metrics_payload

TUSHARE_FINANCIAL_METRICS_PROVIDER = "tushare-financial-metrics"
TUSHARE_FINANCIAL_METRICS_VERSION = "tushare-financial-metrics-v1"
TUSHARE_SOURCE_URL = TUSHARE_API_URL

_INCOME_FIELDS = ",".join(
    [
        "ts_code",
        "ann_date",
        "end_date",
        "report_type",
        "total_revenue",
        "n_income_attr_p",
    ]
)
_FINA_INDICATOR_FIELDS = ",".join(
    [
        "ts_code",
        "ann_date",
        "end_date",
        "q_roe",
        "grossprofit_margin",
        "debt_to_assets",
        "tr_yoy",
        "netprofit_yoy",
        "dt_netprofit_yoy",
    ]
)


class TushareFinancialMetricsProvider:
    provider_name = TUSHARE_FINANCIAL_METRICS_PROVIDER
    provider_version = TUSHARE_FINANCIAL_METRICS_VERSION
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

    def get_financial_metrics(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not self.token:
            self.degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider": self.provider_name,
                    "reason": "TUSHARE_TOKEN is not configured",
                }
            )
            return _unavailable_payload(
                stock_codes=stock_codes,
                retrieved_at=retrieved_at,
            )

        metrics: list[dict[str, Any]] = []
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
                            "Tushare financial metrics currently support A-share stock codes only: "
                            f"{stock_code}"
                        ),
                    }
                )
                continue
            try:
                metrics.append(
                    _build_financial_metric(
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
                        "reason": (
                            f"Tushare financial metrics fetch failed for {stock_code}: {exc}"
                        ),
                    }
                )

        payload = {
            "version": "financial-metrics-v1",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(metrics, failed_stock_codes),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "metrics": metrics,
            "missing_stock_codes": sorted(set(failed_stock_codes)),
        }
        validate_financial_metrics_payload(payload)
        return payload


def _build_financial_metric(
    *,
    ts_code: str,
    token: str,
    fetcher: TushareFetcher | None,
    retrieved_at: str,
) -> dict[str, Any]:
    income_rows = query_tushare_rows(
        token=token,
        api_name="income",
        params={"ts_code": ts_code},
        fields=_INCOME_FIELDS,
        fetcher=fetcher,
    )
    indicator_rows = query_tushare_rows(
        token=token,
        api_name="fina_indicator",
        params={"ts_code": ts_code},
        fields=_FINA_INDICATOR_FIELDS,
        fetcher=fetcher,
    )
    indicator_row = latest_row(indicator_rows, date_fields=("end_date", "ann_date"))
    income_row = _best_matching_income_row(
        income_rows=income_rows,
        indicator_row=indicator_row,
    )
    if indicator_row is None and income_row is None:
        raise ValueError(f"No Tushare financial rows returned for {ts_code}")

    stock_code = ts_code.split(".")[0]
    metadata = stock_basic_metadata(
        ts_code=ts_code,
        token=token,
        fetcher=fetcher,
    )
    report_date = iso_date(
        (indicator_row or {}).get("end_date") or (income_row or {}).get("end_date")
    )
    notice_date = iso_date(
        (income_row or {}).get("ann_date") or (indicator_row or {}).get("ann_date")
    )
    report_type = str((income_row or {}).get("report_type") or "").strip()
    if not report_type:
        report_type = quarter_report_type(report_date)
    return {
        "stock_code": stock_code,
        "stock_name": str(metadata.get("stock_name") or stock_code),
        "report_date": report_date,
        "report_type": report_type,
        "notice_date": notice_date,
        "currency": "CNY",
        "revenue": as_float((income_row or {}).get("total_revenue")),
        "revenue_yoy": as_float((indicator_row or {}).get("tr_yoy")),
        "parent_net_profit": as_float((income_row or {}).get("n_income_attr_p")),
        "parent_net_profit_yoy": as_float((indicator_row or {}).get("netprofit_yoy")),
        "deduct_parent_net_profit_yoy": as_float(
            (indicator_row or {}).get("dt_netprofit_yoy")
        ),
        "roe": as_float((indicator_row or {}).get("q_roe")),
        "gross_margin": as_float((indicator_row or {}).get("grossprofit_margin")),
        "debt_asset_ratio": as_float((indicator_row or {}).get("debt_to_assets")),
        "source": "provider_financial_metrics",
        "source_provider": TUSHARE_FINANCIAL_METRICS_PROVIDER,
        "source_url": get_tushare_api_url(),
        "retrieved_at": retrieved_at,
    }


def _best_matching_income_row(
    *,
    income_rows: list[dict[str, Any]],
    indicator_row: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not income_rows:
        return None
    if indicator_row is None:
        return latest_row(income_rows, date_fields=("end_date", "ann_date"))
    indicator_end_date = str(indicator_row.get("end_date") or "")
    indicator_ann_date = str(indicator_row.get("ann_date") or "")
    for row in income_rows:
        if (
            str(row.get("end_date") or "") == indicator_end_date
            and str(row.get("ann_date") or "") == indicator_ann_date
        ):
            return row
    for row in income_rows:
        if str(row.get("end_date") or "") == indicator_end_date:
            return row
    return latest_row(income_rows, date_fields=("end_date", "ann_date"))


def _data_quality(
    metrics: list[dict[str, Any]],
    missing_stock_codes: list[str],
) -> str:
    if not metrics:
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
        "version": "financial-metrics-v1",
        "provider_name": TUSHARE_FINANCIAL_METRICS_PROVIDER,
        "provider_version": TUSHARE_FINANCIAL_METRICS_VERSION,
        "data_quality": "unavailable",
        "source_url": get_tushare_api_url(),
        "retrieved_at": retrieved_at,
        "metrics": [],
        "missing_stock_codes": sorted(set(str(code) for code in stock_codes)),
    }
    validate_financial_metrics_payload(payload)
    return payload
