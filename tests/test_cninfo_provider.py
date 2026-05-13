from urllib.error import URLError

from src.providers.cninfo import (
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNInfoAnnouncementProvider,
    build_cninfo_announcement_payload,
    build_cninfo_stock_selector,
    normalize_cninfo_announcement_response,
)


def test_builds_cninfo_announcement_payload_for_stock_and_date_range():
    payload = build_cninfo_announcement_payload(
        stock_code="000001",
        start_date="2026-01-01",
        end_date="2026-05-13",
        page_num=2,
        page_size=50,
    )

    assert payload["pageNum"] == 2
    assert payload["pageSize"] == 50
    assert payload["tabName"] == "fulltext"
    assert payload["stock"] == "000001,gssz0000001"
    assert payload["seDate"] == "2026-01-01~2026-05-13"


def test_builds_cninfo_stock_selector_with_exchange_org_id():
    assert build_cninfo_stock_selector("000001") == "000001,gssz0000001"
    assert build_cninfo_stock_selector("300750") == "300750,gssz0300750"
    assert build_cninfo_stock_selector("600519") == "600519,gssh0600519"
    assert build_cninfo_stock_selector("688981") == "688981,gssh0688981"


def test_builds_cninfo_payload_with_market_column_from_stock_code():
    assert (
        build_cninfo_announcement_payload("000001", "2026-01-01", "2026-05-13")[
            "column"
        ]
        == "szse"
    )
    assert (
        build_cninfo_announcement_payload("600519", "2026-01-01", "2026-05-13")[
            "column"
        ]
        == "sse"
    )
    assert (
        build_cninfo_announcement_payload("430047", "2026-01-01", "2026-05-13")[
            "column"
        ]
        == "bj"
    )


def test_normalizes_cninfo_announcement_response():
    response = {
        "announcements": [
            {
                "secCode": "000001",
                "secName": "平安银行",
                "announcementTitle": "2025年度报告",
                "adjunctUrl": "finalpage/2026-03-15/123456.PDF",
                "announcementTime": "2026-03-15",
                "categoryName": "年度报告",
            }
        ]
    }

    announcements = normalize_cninfo_announcement_response(
        response=response,
        stock_code="000001",
    )

    assert announcements == [
        {
            "stock_code": "000001",
            "stock_name": "平安银行",
            "title": "2025年度报告",
            "category": "年度报告",
            "announcement_date": "2026-03-15",
            "source": "cninfo",
            "source_url": "https://static.cninfo.com.cn/finalpage/2026-03-15/123456.PDF",
        }
    ]


def test_cninfo_provider_fetches_announcements_with_injected_fetcher():
    def fake_fetcher(url: str, form_data: dict[str, object], headers: dict[str, str]):
        assert url == CNINFO_ANNOUNCEMENT_QUERY_URL
        assert form_data["stock"] == "000001,gssz0000001"
        assert "User-Agent" in headers
        return {
            "announcements": [
                {
                    "secCode": "000001",
                    "secName": "平安银行",
                    "announcementTitle": "董事会决议公告",
                    "adjunctUrl": "finalpage/2026-05-01/654321.PDF",
                    "announcementTime": "2026-05-01",
                    "categoryName": "董事会",
                }
            ]
        }

    provider = CNInfoAnnouncementProvider(fetcher=fake_fetcher)

    payload = provider.get_announcements(
        stock_codes=["000001"],
        as_of_date="2026-05-13",
    )

    assert payload["version"] == "cninfo-announcement-v1"
    assert payload["data_quality"] == "fresh"
    assert payload["announcements"][0]["title"] == "董事会决议公告"
    assert payload["missing_stock_codes"] == []
    assert provider.degradation_events == []


def test_cninfo_provider_marks_invalid_stock_code_without_fetching():
    def fake_fetcher(
        _url: str,
        _form_data: dict[str, object],
        _headers: dict[str, str],
    ):
        raise AssertionError("invalid stock codes should not call CNINFO")

    provider = CNInfoAnnouncementProvider(fetcher=fake_fetcher)

    payload = provider.get_announcements(
        stock_codes=["not-a-code"],
        as_of_date="2026-05-13",
    )

    assert payload == {
        "version": "cninfo-announcement-v1",
        "data_quality": "unavailable",
        "announcements": [],
        "missing_stock_codes": ["not-a-code"],
    }
    assert provider.degradation_events[0]["type"] == "invalid_stock_code"


def test_cninfo_provider_returns_unavailable_payload_on_fetch_error():
    def failing_fetcher(
        _url: str,
        _form_data: dict[str, object],
        _headers: dict[str, str],
    ):
        raise URLError("network unavailable")

    provider = CNInfoAnnouncementProvider(fetcher=failing_fetcher)

    payload = provider.get_announcements(
        stock_codes=["000001"],
        as_of_date="2026-05-13",
    )

    assert payload == {
        "version": "cninfo-announcement-v1",
        "data_quality": "unavailable",
        "announcements": [],
        "missing_stock_codes": ["000001"],
    }
    assert provider.degradation_events[0]["type"] == "provider_unavailable"
