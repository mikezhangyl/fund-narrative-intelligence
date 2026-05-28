from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import local_env
from src.errors import ProviderContractError
from src.providers.mock import MockDataProvider
from src.providers.provenance import (
    PROVIDER_LAYERS,
    build_provider_foundation,
    layer_from_provider_metadata,
    mock_layer,
)
from src.providers.security_market import tushare_a_share_ts_code
from src.providers.tushare_common import (
    TUSHARE_API_URL,
    TushareFetcher,
    get_tushare_api_url,
    iso_date,
    query_tushare_rows,
)
from src.providers.tushare_common import (
    stock_basic_metadata as query_stock_basic_metadata,
)
from src.validation import validate_fund_payload

TUSHARE_HOLDINGS_PROVIDER = "tushare-fund-portfolio"
TUSHARE_HOLDINGS_VERSION = "tushare-fund-portfolio-v1"
_FUND_PORTFOLIO_FIELDS = ",".join(
    [
        "ts_code",
        "ann_date",
        "end_date",
        "symbol",
        "mkv",
        "amount",
        "stk_mkv_ratio",
        "stk_float_ratio",
        "stk_code",
        "stk_name",
    ]
)


class TushareFundHoldingProvider:
    provider_name = TUSHARE_HOLDINGS_PROVIDER
    provider_version = TUSHARE_HOLDINGS_VERSION
    source_url = TUSHARE_API_URL

    def __init__(
        self,
        *,
        token: str | None = None,
        fetcher: TushareFetcher | None = None,
        fallback_provider: MockDataProvider | None = None,
    ):
        self.token = (
            token if token is not None else local_env.get_config_value("TUSHARE_TOKEN")
        )
        self.fetcher = fetcher
        self.source_url = get_tushare_api_url()
        self.fallback_provider = fallback_provider or MockDataProvider()
        self.degradation_events: list[dict[str, str]] = []

    def get_fund_holdings(self, fund_code: str) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not self.token:
            self.degradation_events.append(
                {
                    "type": "provider_fallback",
                    "requested_provider_mode": "tushare",
                    "fallback_provider_mode": "mock",
                    "reason": "TUSHARE_TOKEN is not configured",
                }
            )
            return self.fallback_provider.get_fund_holdings(fund_code)

        try:
            payload = _build_fund_holdings_payload(
                fund_code=fund_code,
                token=self.token,
                fetcher=self.fetcher,
                retrieved_at=retrieved_at,
            )
            validate_fund_payload(payload, fund_code=fund_code)
            return payload
        except Exception as exc:
            self.degradation_events.append(
                {
                    "type": "provider_fallback",
                    "requested_provider_mode": "tushare",
                    "fallback_provider_mode": "mock",
                    "reason": f"Tushare fund holdings fetch failed: {exc}",
                }
            )
            return self.fallback_provider.get_fund_holdings(fund_code)

    def get_narrative_registry(self) -> dict[str, Any]:
        return self.fallback_provider.get_narrative_registry()

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_stock_narrative_mappings()

    def get_mapping_exclusions(self) -> dict[str, Any]:
        return self.fallback_provider.get_mapping_exclusions()

    def get_evidence(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_evidence()

    def get_signal_events(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_signal_events()

    def get_provider_foundation(
        self,
        fund_provider_metadata: dict[str, Any],
        degradation_events: list[dict[str, str]],
    ) -> dict[str, Any]:
        layers = {layer: mock_layer(layer) for layer in PROVIDER_LAYERS}
        layers["holdings"] = layer_from_provider_metadata(
            layer="holdings",
            provider_metadata=fund_provider_metadata,
            note=(
                "Fund holdings fetched from Tushare fund_portfolio when available; "
                "falls back to V1 mock fixtures on provider failure."
            ),
        )
        return build_provider_foundation(
            layers=layers,
            degradation_events=degradation_events,
        )


def _build_fund_holdings_payload(
    *,
    fund_code: str,
    token: str,
    fetcher: TushareFetcher | None,
    retrieved_at: str,
) -> dict[str, Any]:
    candidate_ts_codes = _candidate_tushare_fund_codes(fund_code)
    candidate_errors: list[str] = []
    for ts_code in candidate_ts_codes:
        rows = query_tushare_rows(
            token=token,
            api_name="fund_portfolio",
            params={"ts_code": ts_code},
            fields=_FUND_PORTFOLIO_FIELDS,
            fetcher=fetcher,
        )
        if not rows:
            candidate_errors.append(f"{ts_code}: empty rows")
            continue
        latest_end_date = max(str(row.get("end_date") or "") for row in rows)
        latest_rows = [
            row for row in rows if str(row.get("end_date") or "") == latest_end_date
        ]
        holdings = _normalize_holdings(latest_rows)
        if not holdings:
            candidate_errors.append(f"{ts_code}: no normalized holdings")
            continue
        holdings = _enrich_holdings(
            holdings=holdings,
            token=token,
            fetcher=fetcher,
        )
        as_of_date = iso_date(latest_end_date)
        return {
            "as_of_date": as_of_date,
            "fund": {
                "fund_code": fund_code,
                "fund_name": f"Tushare Fund {fund_code}",
                "fund_type": "fund",
                "currency": "CNY",
                "provider_metadata": {
                    "provider_name": TUSHARE_HOLDINGS_PROVIDER,
                    "provider_version": TUSHARE_HOLDINGS_VERSION,
                    "source_url": get_tushare_api_url(),
                    "as_of_date": as_of_date,
                    "retrieved_at": retrieved_at,
                    "data_quality": "fresh",
                    "confidence_multiplier": 0.9,
                },
            },
            "holdings": holdings,
        }
    raise ProviderContractError(
        "No Tushare fund_portfolio rows returned for "
        f"{fund_code}; candidates={', '.join(candidate_ts_codes)}; "
        f"errors={'; '.join(candidate_errors) or 'none'}"
    )


def _normalize_holdings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in sorted(rows, key=_holding_sort_key, reverse=True):
        stock_code = _normalize_tushare_holding_code(
            row.get("symbol") or row.get("stk_code") or row.get("stock_code") or ""
        )
        if not stock_code:
            continue
        stock_name = str(
            row.get("stk_name") or row.get("stock_name") or stock_code
        ).strip()
        weight = _ratio_to_weight(row.get("stk_mkv_ratio"))
        if weight is None or weight <= 0:
            continue
        normalized.append(
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "weight": weight,
                "holding_change": 0.0,
                "industry": None,
            }
        )
        if len(normalized) == 10:
            break
    return normalized


def _holding_sort_key(row: dict[str, Any]) -> float:
    ratio = _ratio_to_weight(row.get("stk_mkv_ratio"))
    if ratio is not None:
        return ratio
    try:
        return float(row.get("mkv"))
    except (TypeError, ValueError):
        return 0.0


def _ratio_to_weight(value: Any) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    if numeric > 1:
        numeric = numeric / 100
    return round(numeric, 6)


def _candidate_tushare_fund_codes(fund_code: str) -> list[str]:
    code = str(fund_code or "").strip()
    if not (code.isdigit() and len(code) == 6):
        return [code]
    candidates: list[str] = []
    if code.startswith(("5", "6", "9")):
        candidates.append(f"{code}.SH")
    if code.startswith(("0", "1", "2", "3")):
        candidates.append(f"{code}.SZ")
    candidates.append(f"{code}.OF")
    return list(dict.fromkeys(candidates))


def _normalize_tushare_holding_code(value: Any) -> str:
    code = str(value or "").strip().upper()
    if "." in code:
        code = code.split(".", 1)[0]
    return code


def _enrich_holdings(
    *,
    holdings: list[dict[str, Any]],
    token: str,
    fetcher: TushareFetcher | None,
) -> list[dict[str, Any]]:
    cache: dict[str, dict[str, str]] = {}
    enriched: list[dict[str, Any]] = []
    for holding in holdings:
        stock_code = str(holding.get("stock_code") or "")
        metadata = cache.get(stock_code)
        if metadata is None:
            metadata = _stock_basic_metadata_for_holding(
                stock_code=stock_code,
                token=token,
                fetcher=fetcher,
            )
            cache[stock_code] = metadata
        stock_name = str(metadata.get("stock_name") or holding.get("stock_name") or stock_code)
        industry = metadata.get("industry") or holding.get("industry")
        enriched.append(
            {
                **holding,
                "stock_name": stock_name,
                "industry": industry,
            }
        )
    return enriched


def _stock_basic_metadata_for_holding(
    *,
    stock_code: str,
    token: str,
    fetcher: TushareFetcher | None,
) -> dict[str, str]:
    ts_code = tushare_a_share_ts_code(stock_code)
    if ts_code is None:
        return {}
    return {
        key: value
        for key, value in query_stock_basic_metadata(
            ts_code=ts_code,
            token=token,
            fetcher=fetcher,
        ).items()
        if value is not None
    }
