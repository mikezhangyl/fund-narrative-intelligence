from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from src.market_data.capabilities import (
    DataCapabilityRegistry,
    load_data_capability_registry,
)


@dataclass(frozen=True)
class BreadthScanPlan:
    analysis_capability: str
    required_datasets: tuple[str, ...]
    missing_datasets: tuple[str, ...]
    symbols: tuple[str, ...]
    exchange: str
    start_date: str
    end_date: str
    trade_dates: tuple[str, ...]
    lookback_trading_days: int
    can_run: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BreadthScanPlanner:
    def __init__(self, registry: DataCapabilityRegistry | None = None):
        self.registry = registry or load_data_capability_registry()

    def build_plan(
        self,
        *,
        data_source: Any,
        symbols: list[str] | None = None,
        end_date: str,
        lookback_trading_days: int = 252,
        exchange: str = "SSE",
        analysis_capability: str = "market_breadth_ma20",
    ) -> BreadthScanPlan:
        resolved_symbols = symbols or _symbols_from_metadata(
            data_source.fetch_stock_metadata()
        )
        calendar_start = _calendar_probe_start(
            end_date=end_date,
            lookback_trading_days=lookback_trading_days,
        )
        calendar_rows = data_source.fetch_trade_calendar(
            exchange=exchange,
            start_date=calendar_start,
            end_date=end_date,
        )
        trade_dates = _open_trade_dates(calendar_rows)[-lookback_trading_days:]
        return self._build_plan_from_trade_dates(
            symbols=resolved_symbols,
            trade_dates=trade_dates,
            exchange=exchange,
            lookback_trading_days=lookback_trading_days,
            analysis_capability=analysis_capability,
        )

    def build_static_plan(
        self,
        *,
        symbols: list[str],
        trade_dates: list[str],
        exchange: str = "SSE",
        analysis_capability: str = "market_breadth_ma20",
    ) -> BreadthScanPlan:
        ordered_dates = tuple(sorted({_iso_date(value) for value in trade_dates if value}))
        return self._build_plan_from_trade_dates(
            symbols=symbols,
            trade_dates=ordered_dates,
            exchange=exchange,
            lookback_trading_days=len(ordered_dates),
            analysis_capability=analysis_capability,
        )

    def _build_plan_from_trade_dates(
        self,
        *,
        symbols: list[str],
        trade_dates: tuple[str, ...],
        exchange: str,
        lookback_trading_days: int,
        analysis_capability: str,
    ) -> BreadthScanPlan:
        capability = self.registry.analysis_capability(analysis_capability)
        missing = tuple(self.registry.missing_datasets_for_analysis(analysis_capability))
        blockers = list(missing)
        if not symbols:
            blockers.append("empty_symbol_universe")
        if not trade_dates:
            blockers.append("empty_trade_calendar")
        elif len(trade_dates) < lookback_trading_days:
            blockers.append("insufficient_trade_calendar_history")
        return BreadthScanPlan(
            analysis_capability=analysis_capability,
            required_datasets=capability.required_datasets,
            missing_datasets=missing,
            symbols=tuple(symbols),
            exchange=exchange,
            start_date=trade_dates[0] if trade_dates else "",
            end_date=trade_dates[-1] if trade_dates else "",
            trade_dates=trade_dates,
            lookback_trading_days=lookback_trading_days,
            can_run=not blockers,
            blockers=tuple(blockers),
        )


class BreadthScanner:
    def calculate(self, bars: list[dict[str, Any]]) -> dict[str, Any]:
        by_symbol = _group_by_symbol(bars)
        latest_date = max((str(row.get("trade_date") or "") for row in bars), default="")
        latest_rows = [
            sorted(rows, key=lambda row: str(row.get("trade_date") or ""))[-1]
            for rows in by_symbol.values()
            if rows
        ]
        above_ma20 = 0
        new_high = 0
        new_low = 0
        advance = 0
        decline = 0
        volume_by_date: dict[str, float] = defaultdict(float)

        for rows in by_symbol.values():
            ordered = sorted(rows, key=lambda row: str(row.get("trade_date") or ""))
            latest = ordered[-1]
            close = _as_float(latest.get("close"))
            pre_close = _as_float(latest.get("pre_close"))
            if close is not None and pre_close is not None:
                if close > pre_close:
                    advance += 1
                elif close < pre_close:
                    decline += 1
            closes = [_as_float(row.get("close")) for row in ordered]
            valid_closes = [value for value in closes if value is not None]
            if close is not None and len(valid_closes) >= 20:
                if close > mean(valid_closes[-20:]):
                    above_ma20 += 1
            window_52w = valid_closes[-252:]
            if close is not None and window_52w:
                if close >= max(window_52w):
                    new_high += 1
                if close <= min(window_52w):
                    new_low += 1
            for row in ordered:
                trade_date = str(row.get("trade_date") or "")
                if trade_date:
                    volume_by_date[trade_date] += _as_float(row.get("volume")) or 0.0

        symbol_count = len(latest_rows)
        ordered_volume_dates = sorted(volume_by_date)
        latest_volume = volume_by_date.get(ordered_volume_dates[-1], 0.0) if ordered_volume_dates else 0.0
        prior_volume_values = [
            volume_by_date[trade_date] for trade_date in ordered_volume_dates[-21:-1]
        ]
        prior_volume_avg = mean(prior_volume_values) if prior_volume_values else 0.0
        return {
            "trade_date": latest_date,
            "symbol_count": symbol_count,
            "ma20_breadth": round((above_ma20 / symbol_count) * 100, 4)
            if symbol_count
            else 0.0,
            "advance_count": advance,
            "decline_count": decline,
            "new_high_count": new_high,
            "new_low_count": new_low,
            "volume_expansion": latest_volume > prior_volume_avg if prior_volume_avg else False,
        }


def execute_breadth_scan(
    *,
    data_source: Any,
    plan: BreadthScanPlan,
    scanner: BreadthScanner | None = None,
    include_turnover: bool = True,
) -> dict[str, Any]:
    if not plan.can_run:
        raise ValueError(f"breadth scan plan is not runnable: {', '.join(plan.blockers)}")
    bars, data_fetch_mode = _fetch_breadth_bars(
        data_source=data_source,
        plan=plan,
        include_turnover=include_turnover,
    )
    metrics = (scanner or BreadthScanner()).calculate(bars)
    return {
        "scan_plan": plan.to_dict(),
        "data_fetch_mode": data_fetch_mode,
        "bar_count": len(bars),
        "metrics": metrics,
    }


def _fetch_breadth_bars(
    *,
    data_source: Any,
    plan: BreadthScanPlan,
    include_turnover: bool,
) -> tuple[list[dict[str, Any]], str]:
    fetch_breadth_window = getattr(data_source, "fetch_breadth_window_bars", None)
    if callable(fetch_breadth_window):
        return (
            list(
                fetch_breadth_window(
                    symbols=list(plan.symbols),
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    lookback_trading_days=plan.lookback_trading_days,
                    include_turnover=include_turnover,
                )
            ),
            "breadth_window",
        )
    return (
        list(
            data_source.fetch_daily_bars(
                symbols=list(plan.symbols),
                start_date=plan.start_date,
                end_date=plan.end_date,
                include_turnover=include_turnover,
            )
        ),
        "daily_bars",
    )


def _group_by_symbol(bars: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in bars:
        symbol = str(row.get("symbol") or "")
        if symbol:
            grouped[symbol].append(row)
    return dict(grouped)


def _as_float(value: Any) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _open_trade_dates(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    dates = {
        _iso_date(row.get("cal_date"))
        for row in rows
        if _is_open(row.get("is_open")) and row.get("cal_date")
    }
    return tuple(sorted(date_value for date_value in dates if date_value))


def _symbols_from_metadata(rows: list[dict[str, Any]]) -> list[str]:
    symbols: list[str] = []
    for row in rows:
        symbol = str(row.get("ts_code") or row.get("symbol") or "").strip()
        if symbol:
            symbols.append(symbol)
    return symbols


def _is_open(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() in {"1", "true", "True", "Y", "y"}


def _calendar_probe_start(*, end_date: str, lookback_trading_days: int) -> str:
    end = _parse_date(end_date)
    calendar_days = max(30, lookback_trading_days * 2)
    return (end - timedelta(days=calendar_days)).isoformat()


def _iso_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _parse_date(value: str) -> date:
    text = _iso_date(value)
    return datetime.strptime(text, "%Y-%m-%d").date()
