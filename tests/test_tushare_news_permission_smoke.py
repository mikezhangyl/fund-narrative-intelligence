from __future__ import annotations

import json

from scripts import run_tushare_news_permission_smoke
from src.scanners.tushare_news_permission_smoke import (
    build_tushare_news_permission_smoke,
    render_tushare_news_permission_smoke_html,
)


class FakeNewsSource:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.degradation_events = [{"capability": "news_briefs", "reason": "fake"}]

    def fetch_news_briefs(self, **kwargs):
        src = kwargs["src"]
        response = self.responses[src]
        if isinstance(response, Exception):
            raise response
        return response


def test_tushare_news_permission_smoke_classifies_each_src_and_redacts_failures():
    report = build_tushare_news_permission_smoke(
        source=FakeNewsSource(
            {
                "sina": [
                    {
                        "title": "半导体产业链更新",
                        "source": "sina",
                        "published_at": "2026-06-02T08:00:00+08:00",
                    }
                ],
                "eastmoney": [],
                "cls": RuntimeError("PROVIDER_PERMISSION_REQUIRED token=super-secret"),
            }
        ),
        src_values=["sina", "eastmoney", "cls"],
        start_datetime="2026-06-02 08:00:00",
        end_datetime="2026-06-02 09:00:00",
        limit=3,
        generated_at="2026-06-02T01:00:00+00:00",
    )
    serialized = json.dumps(report, ensure_ascii=False)

    assert report["version"] == "tushare-news-permission-smoke-v1"
    assert report["status"] == "Dev-Ready"
    assert report["summary"] == {
        "src_count": 3,
        "dev_ready_count": 1,
        "paid_permission_required_count": 1,
        "blocked_count": 0,
        "no_data_count": 1,
        "row_count": 1,
    }
    assert {result["src"]: result["status"] for result in report["src_results"]} == {
        "sina": "Dev-Ready",
        "eastmoney": "No Data",
        "cls": "Paid Permission Required",
    }
    assert report["src_results"][0]["sample_rows"][0]["title"] == "半导体产业链更新"
    assert "super-secret" not in serialized
    assert "***REDACTED***" in serialized


def test_tushare_news_permission_smoke_marks_overall_paid_permission_required():
    report = build_tushare_news_permission_smoke(
        source=FakeNewsSource(
            {
                "sina": RuntimeError("PROVIDER_PERMISSION_REQUIRED"),
                "wallstreetcn": RuntimeError("permission denied"),
            }
        ),
        src_values=["sina", "wallstreetcn"],
        start_datetime="2026-06-02 08:00:00",
        end_datetime="2026-06-02 09:00:00",
        limit=3,
    )

    assert report["status"] == "Paid Permission Required"
    assert report["summary"]["paid_permission_required_count"] == 2


def test_tushare_news_permission_smoke_reports_gateway_not_configured_without_provider_call():
    source = FakeNewsSource({"sina": [{"title": "should not be called"}]})
    source.gateway_provider = None

    report = build_tushare_news_permission_smoke(
        source=source,
        src_values=["sina"],
        start_datetime="2026-06-02 08:00:00",
        end_datetime="2026-06-02 09:00:00",
        limit=3,
    )

    assert report["status"] == "Blocked"
    assert report["environment_diagnostics"] == {
        "market_data_gateway_configured": False,
        "gateway_provider_loaded": False,
    }
    assert report["src_results"] == [
        {
            "src": "sina",
            "status": "Blocked",
            "row_count": 0,
            "sample_rows": [],
            "failure_reason": (
                "MARKET_DATA_GATEWAY_URL is not configured; gateway source boundary "
                "cannot be reached."
            ),
        }
    ]


def test_tushare_news_permission_smoke_html_is_chinese_and_actionable():
    html = render_tushare_news_permission_smoke_html(
        build_tushare_news_permission_smoke(
            source=FakeNewsSource({"sina": []}),
            src_values=["sina"],
            start_datetime="2026-06-02 08:00:00",
            end_datetime="2026-06-02 09:00:00",
            limit=3,
        )
    )

    assert "<h1>Tushare news 权限与 live smoke</h1>" in html
    assert "Dev-Ready" in html
    assert "<strong>Dev-Ready:</strong> 0" in html
    assert "Paid Permission Required" in html
    assert "不新增认证机制" in html


def test_tushare_news_permission_smoke_cli_writes_json_and_html(monkeypatch, tmp_path):
    class FakeSourceFactory:
        def __init__(self) -> None:
            self.source = FakeNewsSource({"sina": [{"title": "A股新闻", "source": "sina"}]})

        def fetch_news_briefs(self, **kwargs):
            return self.source.fetch_news_briefs(**kwargs)

        @property
        def degradation_events(self):
            return self.source.degradation_events

    monkeypatch.setattr(
        run_tushare_news_permission_smoke,
        "ConsolidatedMarketDataSource",
        FakeSourceFactory,
    )

    exit_code = run_tushare_news_permission_smoke.main(
        [
            "--src",
            "sina",
            "--start-datetime",
            "2026-06-02 08:00:00",
            "--end-datetime",
            "2026-06-02 09:00:00",
            "--output-dir",
            str(tmp_path),
        ]
    )
    payload = json.loads((tmp_path / "tushare_news_permission_smoke.json").read_text())

    assert exit_code == 0
    assert payload["status"] == "Dev-Ready"
    assert "<h1>Tushare news 权限与 live smoke</h1>" in (
        tmp_path / "tushare_news_permission_smoke.html"
    ).read_text()
