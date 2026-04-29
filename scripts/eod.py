"""
EOD data helper. Fetches current Alpaca paper positions, computes P&L,
checks trailing stops, updates memory/positions.md and memory/highwatermarks.json.

Prints a JSON summary to stdout for the EOD routine prompt to consume.

Usage:
    python scripts/eod.py
    python scripts/eod.py --dry-run   (skip file writes, still prints JSON)
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import skills.alpaca as alpaca
from skills.timeseries import benchmarks, recorder

ET = ZoneInfo("America/New_York")
TRAILING_STOP_PCT = 0.15
HWM_FILE = ROOT / "memory" / "highwatermarks.json"
POSITIONS_FILE = ROOT / "memory" / "positions.md"
PORTFOLIO_CSV = recorder.PORTFOLIO_CSV
POSITIONS_CSV = recorder.POSITIONS_CSV
BENCHMARKS_CSV = recorder.BENCHMARKS_CSV
STARTING_EQUITY = 100_000.0


def load_hwm() -> dict:
    if HWM_FILE.exists():
        return json.loads(HWM_FILE.read_text(encoding="utf-8"))
    return {}


def save_hwm(hwm: dict) -> None:
    HWM_FILE.parent.mkdir(exist_ok=True)
    HWM_FILE.write_text(json.dumps(hwm, indent=2), encoding="utf-8")


def update_positions_md(positions: list[dict], acct: alpaca.AccountState, today: str) -> None:
    lines = [
        "# Current Paper Positions\n\n",
        "> Source of truth for open Alpaca paper positions.\n",
        "> Updated by every routine that changes positions (market-open, midday, EOD).\n",
        "> Never manually edit - only routines write here.\n\n",
        f"Last updated: {today} (EOD routine)\n\n---\n\n",
    ]

    if not positions:
        lines.append("## Open positions\n\n*(None - fully in cash)*\n\n")
    else:
        lines.append("## Open positions\n\n")
        lines.append("| Ticker | Shares | Avg cost | Current price | Market value | % of equity | Entry date | Regime at entry |\n")
        lines.append("|--------|--------|----------|---------------|--------------|-------------|------------|------------------|\n")
        for p in positions:
            pct = p["market_value"] / acct.equity * 100 if acct.equity else 0
            entry = p.get("entry_date", today)
            lines.append(
                f"| {p['ticker']} | {p['qty']:.4f} | ${p['avg_cost']:,.2f} | "
                f"${p['current_price']:,.2f} | ${p['market_value']:,.2f} | "
                f"{pct:.1f}% | {entry} | RISK-ON |\n"
            )

    lines.append(f"\n## Account summary\n\n| Field | Value |\n|-------|-------|\n")
    lines.append(f"| Equity | ${acct.equity:,.2f} |\n")
    lines.append(f"| Cash | ${acct.cash:,.2f} |\n")
    lines.append(f"| Buying power | ${acct.buying_power:,.2f} |\n")

    POSITIONS_FILE.write_text("".join(lines), encoding="utf-8")


def main(dry_run: bool) -> dict:
    today = date.today().isoformat()
    acct = alpaca.get_account()
    raw_positions = alpaca.get_positions()
    hwm = load_hwm()

    enriched = []
    stop_alerts = []

    for p in raw_positions:
        ticker = p["ticker"]
        price = p["current_price"]

        # Initialise or update high-water mark
        if ticker not in hwm:
            hwm[ticker] = {"hwm": price, "hwm_date": today, "entry_date": today}
        elif price > hwm[ticker]["hwm"]:
            hwm[ticker]["hwm"] = price
            hwm[ticker]["hwm_date"] = today

        entry_date = hwm[ticker].get("entry_date", today)
        hwm_price = hwm[ticker]["hwm"]
        pct_from_hwm = (price - hwm_price) / hwm_price * 100
        stop_triggered = pct_from_hwm <= -(TRAILING_STOP_PCT * 100)

        record = {
            **p,
            "entry_date": entry_date,
            "pct_of_equity": p["market_value"] / acct.equity * 100 if acct.equity else 0,
            "unrealized_pl_pct": p["unrealized_pl"] / (p["avg_cost"] * p["qty"]) * 100 if p["qty"] else 0,
            "hwm": hwm_price,
            "hwm_date": hwm[ticker]["hwm_date"],
            "pct_from_hwm": round(pct_from_hwm, 2),
            "stop_triggered": stop_triggered,
        }
        enriched.append(record)

        if stop_triggered:
            stop_alerts.append({
                "ticker": ticker,
                "current_price": price,
                "hwm": hwm_price,
                "pct_from_hwm": round(pct_from_hwm, 2),
                "action": "EXIT at market open tomorrow per Rule 5.2",
            })

    total_unrealized = sum(p["unrealized_pl"] for p in enriched)
    total_pl_pct = total_unrealized / STARTING_EQUITY * 100

    summary = {
        "date": today,
        "account": {
            "equity": acct.equity,
            "cash": acct.cash,
            "buying_power": acct.buying_power,
        },
        "positions": enriched,
        "totals": {
            "portfolio_value": acct.equity,
            "starting_equity": STARTING_EQUITY,
            "total_unrealized_pl": round(total_unrealized, 2),
            "total_unrealized_pl_pct": round(total_pl_pct, 4),
            "cash_pct": round(acct.cash / acct.equity * 100, 2) if acct.equity else 100.0,
            "position_count": len(enriched),
        },
        "trailing_stop_alerts": stop_alerts,
        "dry_run": dry_run,
    }

    timeseries_status = {"portfolio": False, "positions": 0, "benchmarks": 0, "error": None}
    if not dry_run:
        save_hwm(hwm)
        update_positions_md(enriched, acct, today)

        positions_value = acct.equity - acct.cash
        recorder.record_portfolio(
            date=today,
            equity=acct.equity,
            cash=acct.cash,
            positions_value=positions_value,
            starting_equity=STARTING_EQUITY,
            path=PORTFOLIO_CSV,
        )
        timeseries_status["portfolio"] = True
        timeseries_status["positions"] = recorder.record_positions(
            date=today,
            positions=raw_positions,
            portfolio_equity=acct.equity,
            path=POSITIONS_CSV,
        )
        try:
            closes = benchmarks.get_closes_for_date(
                benchmarks.DEFAULT_BENCHMARKS, date.today()
            )
            timeseries_status["benchmarks"] = recorder.record_benchmarks(
                date=today, closes=closes, path=BENCHMARKS_CSV
            )
        except Exception as exc:
            timeseries_status["error"] = f"benchmark fetch failed: {exc}"

    summary["timeseries"] = timeseries_status
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = main(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
