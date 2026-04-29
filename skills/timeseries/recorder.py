"""
Idempotent CSV writers for the bot's daily performance time series.

Three append-only CSVs in memory/timeseries/. Re-running for the same date
overwrites that day's rows; never duplicates. All `_pct` columns are stored
as decimal ratios (0.0123 means 1.23%).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMESERIES_DIR = ROOT / "memory" / "timeseries"

PORTFOLIO_CSV = TIMESERIES_DIR / "portfolio_daily.csv"
POSITIONS_CSV = TIMESERIES_DIR / "positions_daily.csv"
BENCHMARKS_CSV = TIMESERIES_DIR / "benchmarks_daily.csv"

PORTFOLIO_FIELDS = [
    "date", "equity", "cash", "positions_value",
    "daily_pnl", "daily_pnl_pct",
    "cumulative_pnl", "cumulative_pnl_pct",
]
POSITIONS_FIELDS = [
    "date", "ticker", "quantity", "avg_cost", "market_price",
    "market_value", "unrealized_pnl", "weight_pct",
]
BENCHMARKS_FIELDS = [
    "date", "benchmark", "close_price",
    "daily_return_pct", "cumulative_return_pct",
]

BLEND_NAME = "60_40_BLEND"
BLEND_SPY_WEIGHT = 0.6
BLEND_AGG_WEIGHT = 0.4


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _fmt(value: float, decimals: int) -> str:
    return f"{float(value):.{decimals}f}"


def record_portfolio(
    *,
    date: str,
    equity: float,
    cash: float,
    positions_value: float,
    starting_equity: float,
    path: Path | None = None,
) -> dict:
    """
    Append or update today's portfolio row, then recompute daily/cumulative
    columns for the entire CSV so the series stays internally consistent.
    Returns the row written for `date`.
    """
    target = path or PORTFOLIO_CSV
    rows = [r for r in _read(target) if r["date"] != date]
    rows.append({
        "date": date,
        "equity": _fmt(equity, 2),
        "cash": _fmt(cash, 2),
        "positions_value": _fmt(positions_value, 2),
        "daily_pnl": "",
        "daily_pnl_pct": "",
        "cumulative_pnl": "",
        "cumulative_pnl_pct": "",
    })
    rows.sort(key=lambda r: r["date"])

    prior_equity = starting_equity
    for row in rows:
        eq = float(row["equity"])
        daily_pnl = eq - prior_equity
        daily_pct = (daily_pnl / prior_equity) if prior_equity else 0.0
        cum_pnl = eq - starting_equity
        cum_pct = (cum_pnl / starting_equity) if starting_equity else 0.0
        row["daily_pnl"] = _fmt(daily_pnl, 2)
        row["daily_pnl_pct"] = _fmt(daily_pct, 8)
        row["cumulative_pnl"] = _fmt(cum_pnl, 2)
        row["cumulative_pnl_pct"] = _fmt(cum_pct, 8)
        prior_equity = eq

    _write(target, PORTFOLIO_FIELDS, rows)
    return next(r for r in rows if r["date"] == date)


def record_positions(
    *,
    date: str,
    positions: list[dict],
    portfolio_equity: float,
    path: Path | None = None,
) -> int:
    """
    Replace today's position rows. Each input dict must have keys
    ticker, qty, avg_cost, current_price, market_value, unrealized_pl
    (the shape returned by skills.alpaca.get_positions).
    Returns the number of position rows written for `date`.
    """
    target = path or POSITIONS_CSV
    rows = [r for r in _read(target) if r["date"] != date]
    new_rows = []
    for p in positions:
        weight = (p["market_value"] / portfolio_equity) if portfolio_equity else 0.0
        new_rows.append({
            "date": date,
            "ticker": p["ticker"],
            "quantity": _fmt(p["qty"], 6),
            "avg_cost": _fmt(p["avg_cost"], 4),
            "market_price": _fmt(p["current_price"], 4),
            "market_value": _fmt(p["market_value"], 2),
            "unrealized_pnl": _fmt(p["unrealized_pl"], 2),
            "weight_pct": _fmt(weight, 8),
        })
    rows.extend(new_rows)
    rows.sort(key=lambda r: (r["date"], r["ticker"]))
    _write(target, POSITIONS_FIELDS, rows)
    return len(new_rows)


def record_benchmarks(
    *,
    date: str,
    closes: dict[str, float],
    path: Path | None = None,
) -> int:
    """
    Replace today's benchmark rows for every symbol in `closes`. If both SPY
    and AGG are present, also writes a `60_40_BLEND` row (close_price empty,
    daily/cumulative computed from SPY+AGG daily returns rebalanced daily).
    Recomputes returns across the full series. Returns rows written for `date`.
    """
    target = path or BENCHMARKS_CSV
    rows = [r for r in _read(target) if r["date"] != date]
    written = 0
    for bm, close in closes.items():
        rows.append({
            "date": date,
            "benchmark": bm,
            "close_price": _fmt(close, 6),
            "daily_return_pct": "",
            "cumulative_return_pct": "",
        })
        written += 1
    include_blend = "SPY" in closes and "AGG" in closes
    if include_blend:
        rows.append({
            "date": date,
            "benchmark": BLEND_NAME,
            "close_price": "",
            "daily_return_pct": "",
            "cumulative_return_pct": "",
        })
        written += 1

    rows.sort(key=lambda r: (r["benchmark"], r["date"]))

    by_bm: dict[str, list[dict]] = {}
    for row in rows:
        by_bm.setdefault(row["benchmark"], []).append(row)

    # First pass: priced benchmarks (anything with close_price set)
    for bm, series in by_bm.items():
        if bm == BLEND_NAME:
            continue
        start_close: float | None = None
        prior_close: float | None = None
        for row in series:
            if row["close_price"] == "":
                row["daily_return_pct"] = ""
                row["cumulative_return_pct"] = ""
                continue
            close = float(row["close_price"])
            if start_close is None:
                start_close = close
            daily = ((close - prior_close) / prior_close) if prior_close else 0.0
            cum = ((close - start_close) / start_close) if start_close else 0.0
            row["daily_return_pct"] = _fmt(daily, 8)
            row["cumulative_return_pct"] = _fmt(cum, 8)
            prior_close = close

    # Second pass: 60/40 blend, daily-rebalanced, computed from SPY+AGG dailies.
    if BLEND_NAME in by_bm:
        spy_by_date = {r["date"]: r for r in by_bm.get("SPY", [])}
        agg_by_date = {r["date"]: r for r in by_bm.get("AGG", [])}
        cum_factor = 1.0
        for row in by_bm[BLEND_NAME]:
            d = row["date"]
            spy = spy_by_date.get(d)
            agg = agg_by_date.get(d)
            if not spy or not agg or spy["daily_return_pct"] == "" or agg["daily_return_pct"] == "":
                row["daily_return_pct"] = ""
                row["cumulative_return_pct"] = ""
                continue
            daily = BLEND_SPY_WEIGHT * float(spy["daily_return_pct"]) + BLEND_AGG_WEIGHT * float(agg["daily_return_pct"])
            cum_factor *= (1 + daily)
            row["daily_return_pct"] = _fmt(daily, 8)
            row["cumulative_return_pct"] = _fmt(cum_factor - 1, 8)

    _write(target, BENCHMARKS_FIELDS, rows)
    return written
