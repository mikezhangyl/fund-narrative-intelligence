from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CNINFO_ANNOUNCEMENT_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE_URL = "https://static.cninfo.com.cn/"

CNInfoFetcher = Callable[[str, dict[str, object], dict[str, str]], dict[str, Any]]


class CNInfoAnnouncementProvider:
    provider_name = "cninfo-announcement"
    provider_version = "cninfo-announcement-v1"
    data_quality = "fresh"

    def __init__(self, fetcher: CNInfoFetcher | None = None):
        self.fetcher = fetcher or _fetch_cninfo_json
        self.degradation_events: list[dict[str, str]] = []

    def get_announcements(
        self,
        stock_codes: list[str],
        as_of_date: str,
        start_date: str | None = None,
    ) -> dict[str, Any]:
        announcements: list[dict[str, Any]] = []
        missing_stock_codes: list[str] = []
        requested_stock_codes = sorted(set(stock_codes))
        for raw_stock_code in requested_stock_codes:
            stock_code = _normalize_stock_code(raw_stock_code)
            if stock_code is None:
                missing_stock_codes.append(str(raw_stock_code))
                self.degradation_events.append(
                    {
                        "type": "invalid_stock_code",
                        "provider_name": self.provider_name,
                        "reason": f"Invalid CNINFO stock code: {raw_stock_code}",
                    }
                )
                continue

            form_data = build_cninfo_announcement_payload(
                stock_code=stock_code,
                start_date=start_date or as_of_date,
                end_date=as_of_date,
            )
            try:
                response = self.fetcher(
                    CNINFO_ANNOUNCEMENT_QUERY_URL,
                    form_data,
                    _default_headers(),
                )
            except Exception as exc:
                self.degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider_name": self.provider_name,
                        "reason": f"CNINFO announcement fetch failed for {stock_code}: {exc}",
                    }
                )
                missing_stock_codes.append(stock_code)
                continue

            normalized = normalize_cninfo_announcement_response(
                response=response,
                stock_code=stock_code,
            )
            announcements.extend(normalized)

        return {
            "version": self.provider_version,
            "data_quality": _data_quality(
                requested_count=len(requested_stock_codes),
                missing_count=len(missing_stock_codes),
            ),
            "announcements": announcements,
            "missing_stock_codes": missing_stock_codes,
        }


def build_cninfo_announcement_payload(
    stock_code: str,
    start_date: str,
    end_date: str,
    page_num: int = 1,
    page_size: int = 30,
) -> dict[str, object]:
    normalized_stock_code = _require_stock_code(stock_code)
    return {
        "pageNum": page_num,
        "pageSize": page_size,
        "column": _cninfo_column_for_stock_code(normalized_stock_code),
        "tabName": "fulltext",
        "plate": "",
        "stock": normalized_stock_code,
        "searchkey": "",
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": f"{start_date}~{end_date}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }


def normalize_cninfo_announcement_response(
    response: dict[str, Any],
    stock_code: str,
) -> list[dict[str, Any]]:
    announcements = response.get("announcements")
    if not isinstance(announcements, list):
        return []

    return [
        {
            "stock_code": str(item.get("secCode") or stock_code),
            "stock_name": _clean_text(item.get("secName") or ""),
            "title": _clean_text(item.get("announcementTitle") or ""),
            "category": _clean_text(item.get("categoryName") or ""),
            "announcement_date": _announcement_date(item.get("announcementTime")),
            "source": "cninfo",
            "source_url": _source_url(item.get("adjunctUrl")),
        }
        for item in announcements
        if isinstance(item, dict)
    ]


def _fetch_cninfo_json(
    url: str,
    form_data: dict[str, object],
    headers: dict[str, str],
) -> dict[str, Any]:
    body = urlencode(form_data).encode("utf-8")
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _default_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.cninfo.com.cn/new/index",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json,text/plain,*/*",
    }


def _data_quality(requested_count: int, missing_count: int) -> str:
    if requested_count == 0:
        return "unavailable"
    if missing_count == 0:
        return "fresh"
    if missing_count == requested_count:
        return "unavailable"
    return "partial"


def _announcement_date(value: Any) -> str | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return None


def _source_url(value: Any) -> str | None:
    if not value:
        return None
    path = str(value).strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return CNINFO_STATIC_BASE_URL + path.lstrip("/")


def _clean_text(value: Any) -> str:
    text = unescape(str(value)).strip()
    return re.sub(r"<[^>]+>", "", text)


def _require_stock_code(stock_code: str) -> str:
    normalized = _normalize_stock_code(stock_code)
    if normalized is None:
        raise ValueError(f"Invalid CNINFO stock code: {stock_code}")
    return normalized


def _normalize_stock_code(stock_code: str) -> str | None:
    normalized = str(stock_code).strip()
    if not re.fullmatch(r"\d{6}", normalized):
        return None
    return normalized


def _cninfo_column_for_stock_code(stock_code: str) -> str:
    if stock_code.startswith(("6", "9")):
        return "sse"
    if stock_code.startswith(("4", "8")):
        return "bj"
    return "szse"
