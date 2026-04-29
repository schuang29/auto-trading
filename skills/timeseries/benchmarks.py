"""
Benchmark close-price fetcher. Pulls daily bars from Alpaca for SPY, AGG, VT.

Used by the EOD recorder (single date) and the backfill script (date range).
The 60/40 blend is computed by the recorder, not here — this module only
fetches priced benchmarks.
"""
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

load_dotenv()

DEFAULT_BENCHMARKS = ["SPY", "AGG", "VT"]
BACKFILL_START = date(2026, 4, 19)


def _client() -> StockHistoricalDataClient:
    return StockHistoricalDataClient(
        os.environ["ALPACA_API_KEY"],
        os.environ["ALPACA_SECRET_KEY"],
    )


def get_closes_in_range(
    symbols: list[str],
    start: date,
    end: date,
) -> dict[date, dict[str, float]]:
    """
    Return a mapping of trading_date -> {symbol: close_price} over [start, end].
    Days where no symbol has a bar (weekends, holidays) are simply absent.
    """
    req = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=datetime.combine(start, time.min, tzinfo=timezone.utc),
        end=datetime.combine(end, time.max, tzinfo=timezone.utc),
        feed=DataFeed.IEX,  # free-tier compatible; full SIP requires paid subscription
    )
    response = _client().get_stock_bars(req)
    raw = response.data  # dict[symbol, list[Bar]]

    out: dict[date, dict[str, float]] = {}
    for symbol, bars in raw.items():
        for bar in bars:
            d = bar.timestamp.date()
            out.setdefault(d, {})[symbol] = float(bar.close)
    return out


def get_closes_for_date(
    symbols: list[str],
    target: date,
    lookback_days: int = 7,
) -> dict[str, float]:
    """
    Return closes for `target`. If no bars on that exact date (e.g. holiday,
    or end-of-day data not yet posted), returns the most recent prior trading
    day's closes within `lookback_days`. Raises if nothing in range.
    """
    start = target - timedelta(days=lookback_days)
    series = get_closes_in_range(symbols, start, target)
    if not series:
        raise RuntimeError(
            f"No benchmark bars in [{start}, {target}] for {symbols}"
        )
    latest = max(series.keys())
    return series[latest]
