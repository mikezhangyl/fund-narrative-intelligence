from __future__ import annotations

from src.providers import tushare_common
from src.providers.tushare_market import TushareMarketDataProvider


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return b'{"code":0,"data":{"fields":[],"items":[]}}'


def test_post_tushare_query_uses_default_official_url(monkeypatch):
    captured_urls: list[str] = []
    monkeypatch.setattr(tushare_common.local_env, "get_config_value", lambda name: None)
    monkeypatch.setattr(
        tushare_common,
        "urlopen",
        lambda request, timeout: captured_urls.append(request.full_url) or _Response(),
    )

    tushare_common._post_tushare_query(
        token="token",
        params={},
        fields="",
        api_name="daily",
    )

    assert captured_urls == ["https://api.tushare.pro"]


def test_post_tushare_query_uses_configured_gateway_url(monkeypatch):
    captured_urls: list[str] = []
    monkeypatch.setattr(
        tushare_common.local_env,
        "get_config_value",
        lambda name: "http://127.0.0.1:8700/tushare"
        if name == "TUSHARE_API_URL"
        else None,
    )
    monkeypatch.setattr(
        tushare_common,
        "urlopen",
        lambda request, timeout: captured_urls.append(request.full_url) or _Response(),
    )

    tushare_common._post_tushare_query(
        token="token",
        params={},
        fields="",
        api_name="daily",
    )

    assert captured_urls == ["http://127.0.0.1:8700/tushare"]


def test_tushare_provider_source_url_uses_configured_gateway(monkeypatch):
    monkeypatch.setattr(
        tushare_common.local_env,
        "get_config_value",
        lambda name: "http://127.0.0.1:8700/tushare"
        if name == "TUSHARE_API_URL"
        else "token"
        if name == "TUSHARE_TOKEN"
        else None,
    )

    provider = TushareMarketDataProvider(fetcher=lambda *args: {})

    assert provider.source_url == "http://127.0.0.1:8700/tushare"
