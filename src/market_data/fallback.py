from __future__ import annotations

from typing import Any, Callable


class FallbackMarketDataProvider:
    provider_name = "fallback-market-data-provider"

    def __init__(self, *, primary: Any, fallback: Any):
        self.primary = primary
        self.fallback = fallback
        self.degradation_events: list[dict[str, str]] = []

    def fetch_daily_bars(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self._call_with_fallback("fetch_daily_bars", **kwargs)

    def fetch_sector_data(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self._call_with_fallback("fetch_sector_data", **kwargs)

    def fetch_etf_data(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self._call_with_fallback("fetch_etf_data", **kwargs)

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "primary": _health(self.primary),
            "fallback": _health(self.fallback),
        }

    def _call_with_fallback(self, method_name: str, **kwargs: Any) -> list[dict[str, Any]]:
        primary_method = _method(self.primary, method_name)
        try:
            return primary_method(**kwargs)
        except Exception as exc:
            self.degradation_events.append(
                {
                    "type": "provider_fallback",
                    "primary_provider": str(
                        getattr(self.primary, "provider_name", "primary")
                    ),
                    "fallback_provider": str(
                        getattr(self.fallback, "provider_name", "fallback")
                    ),
                    "reason": str(exc),
                }
            )
            fallback_method = _method(self.fallback, method_name)
            return fallback_method(**kwargs)


def _method(provider: Any, method_name: str) -> Callable[..., list[dict[str, Any]]]:
    method = getattr(provider, method_name, None)
    if not callable(method):
        raise AttributeError(f"{provider!r} does not support {method_name}")
    return method


def _health(provider: Any) -> dict[str, Any]:
    health_check = getattr(provider, "health_check", None)
    if not callable(health_check):
        return {
            "provider": str(getattr(provider, "provider_name", "unknown")),
            "ok": False,
            "error": "health_check is not implemented",
        }
    return dict(health_check())
