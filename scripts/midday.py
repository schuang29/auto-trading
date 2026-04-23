"""
Midday data helper. Fetches current Alpaca paper positions, updates
high-water marks, checks trailing stops, and flags large intraday movers.

Does NOT update memory/positions.md (that is EOD's responsibility).

Prints a JSON summary to stdout for the midday routine prompt to consume.

Usage:
    python scripts/midday.py
    python scripts/midday.py --dry-run   (skip HWM file write, still prints JSON)
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

ET = ZoneInfo("America/New_York")
TRAILING_STOP_PCT = 0.15
LARGE_MOVER_THRESHOLD = 0.02   # flag intraday move >= 2%
HWM_FILE = ROOT / "memory" / "highwatermarks.json"


def load_hwm() -> dict:
    if HWM_FILE.exists():
        return json.loads(HWM_FILE.read_text(encoding="utf-8"))
    return {}


def save_hwm(hwm: dict) -> None:
    HWM_FILE.parent.mkdir(exist_ok=True)
    HWM_FILE.write_text(json.dumps(hwm, indent=2), encoding="utf-8")


def main(dry_run: bool) -> dict:
    today = date.today().isoformat()
    now_et = datetime.now(ET).strftime("%H:%M ET")
    acct = alpaca.get_account()
    raw_positions = alpaca.get_positions()
    hwm = load_hwm()

    enriched = []
    stop_alerts = []
    large_movers = []

    for p in raw_positions:
        ticker = p["ticker"]
        price = p["current_price"]

        # Initialise or update high-water mark
        if ticker not in hwm:
            hwm[ticker] = {"hwm": price, "hwm_date": today, "entry_date": today}
        elif price > hwm[ticker]["hwm"]:
            hwm[ticker]["hwm"] = price
            hwm[ticker]["hwm_date"] = today

        hwm_price = hwm[ticker]["hwm"]
        pct_from_hwm = (price - hwm_price) / hwm_price * 100
        stop_triggered = pct_from_hwm <= -(TRAILING_STOP_PCT * 100)

        intraday_plpc = p["unrealized_intraday_plpc"] * 100  # SDK returns decimal

        record = {
            "ticker": ticker,
            "current_price": price,
            "market_value": p["market_value"],
            "unrealized_pl": p["unrealized_pl"],
            "unrealized_intraday_pl": p["unrealized_intraday_pl"],
            "unrealized_intraday_plpc": round(intraday_plpc, 2),
            "hwm": hwm_price,
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

        if abs(intraday_plpc) >= LARGE_MOVER_THRESHOLD * 100:
            large_movers.append({
                "ticker": ticker,
                "intraday_plpc": round(intraday_plpc, 2),
                "current_price": price,
            })

    summary = {
        "date": today,
        "time": now_et,
        "account": {
            "equity": acct.equity,
            "cash": acct.cash,
        },
        "positions": enriched,
        "trailing_stop_alerts": stop_alerts,
        "large_movers": large_movers,
        "dry_run": dry_run,
    }

    if not dry_run:
        save_hwm(hwm)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = main(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
