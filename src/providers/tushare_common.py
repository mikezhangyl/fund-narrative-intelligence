from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen

from src import local_env
from src.errors import ProviderContractError, ProviderFetchError

TushareFetcher = Callable[[str, dict[str, Any], str, str], dict[str, Any]]
DEFAULT_TUSHARE_API_URL = "https://api.tushare.pro"
TUSHARE_API_URL = DEFAULT_TUSHARE_API_URL
_STOCK_BASIC_FIELDS = "ts_code,symbol,name,industry"


def get_tushare_api_url() -> str:
    configured_url = local_env.get_config_value("TUSHARE_API_URL")
    if configured_url:
        stripped_url = configured_url.strip()
        if stripped_url:
            return stripped_url
    return DEFAULT_TUSHARE_API_URL


def query_tushare_rows(
    *,
    token: str,
    api_name: str,
    params: dict[str, Any],
    fields: str,
    fetcher: TushareFetcher | None = None,
) -> list[dict[str, Any]]:
    response = (fetcher or _post_tushare_query)(token, params, fields, api_name)
    if not isinstance(response, dict):
        raise ProviderContractError(f"Tushare {api_name} response must be an object")
    code = response.get("code")
    if code not in (0, None):
        message = str(response.get("msg") or f"code={code}")
        raise ProviderFetchError(f"Tushare {api_name} failed: {message}")
    data = response.get("data")
    if not isinstance(data, dict):
        raise ProviderContractError(f"Tushare {api_name} response missing data object")
    raw_fields = data.get("fields")
    raw_items = data.get("items")
    if not isinstance(raw_fields, list) or not all(
        isinstance(field, str) and field for field in raw_fields
    ):
        raise ProviderContractError(f"Tushare {api_name} response fields must be a string list")
    if not isinstance(raw_items, list):
        raise ProviderContractError(f"Tushare {api_name} response items must be a list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, list):
            raise ProviderContractError(
                f"Tushare {api_name} response items[{index}] must be a list"
            )
        if len(item) != len(raw_fields):
            raise ProviderContractError(
                f"Tushare {api_name} response row width does not match fields"
            )
        rows.append(dict(zip(raw_fields, item, strict=True)))
    return rows


def latest_row(
    rows: list[dict[str, Any]],
    *,
    date_fields: tuple[str, ...],
) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: tuple(str(row.get(field) or "") for field in date_fields),
    )


def iso_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def quarter_report_type(end_date: str) -> str:
    if end_date.endswith("03-31") or end_date.endswith("0331"):
        return "一季报"
    if end_date.endswith("06-30") or end_date.endswith("0630"):
        return "中报"
    if end_date.endswith("09-30") or end_date.endswith("0930"):
        return "三季报"
    if end_date.endswith("12-31") or end_date.endswith("1231"):
        return "年报"
    return "财报"


def as_float(value: Any) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stock_basic_metadata(
    *,
    ts_code: str,
    token: str,
    fetcher: TushareFetcher | None = None,
) -> dict[str, str | None]:
    rows = query_tushare_rows(
        token=token,
        api_name="stock_basic",
        params={"ts_code": ts_code},
        fields=_STOCK_BASIC_FIELDS,
        fetcher=fetcher,
    )
    if not rows:
        return {}
    row = rows[0]
    return {
        "stock_name": str(row.get("name") or ts_code).strip(),
        "industry": str(row.get("industry") or "").strip() or None,
    }


def _post_tushare_query(
    token: str,
    params: dict[str, Any],
    fields: str,
    api_name: str,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "api_name": api_name,
            "token": token,
            "params": params,
            "fields": fields,
        }
    ).encode("utf-8")
    request = Request(
        get_tushare_api_url(),
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ProviderFetchError(f"Failed to fetch Tushare {api_name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderContractError(f"Tushare {api_name} response must be an object")
    return payload
