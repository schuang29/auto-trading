"""
Market-open execution script. Runs at 9:35 AM ET.

Reads today's proposals from memory/proposals/YYYY-MM-DD.json,
runs each through the guardrail checker, places approved orders on
Alpaca paper, and logs decisions to memory/decisions/.

Usage:
    python scripts/market_open.py
    python scripts/market_open.py --dry-run
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.guardrails.checker import run_checks
import skills.alpaca as alpaca

ET = ZoneInfo("America/New_York")


def load_proposals(today: str) -> dict:
    path = ROOT / "memory" / "proposals" / f"{today}.json"
    if not path.exists():
        print(f"ERROR: No proposals file found at {path}")
        print("The pre-market routine must run first and write proposals.")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def log_decision(ticker: str, side: str, notional: float, order_id: str,
                 rule: str, regime: str, price_est: float | None, dry_run: bool) -> None:
    now = datetime.now(ET)
    stamp = now.strftime("%Y-%m-%d-%H%M")
    fname = f"{stamp}-{ticker}-{side.upper()}.md"
    path = ROOT / "memory" / "decisions" / fname
    path.parent.mkdir(exist_ok=True)

    content = f"""# Decision — {ticker} {side.upper()} — {now.strftime("%Y-%m-%d %H:%M ET")}

| Field | Value |
|-------|-------|
| Ticker | {ticker} |
| Side | {side.upper()} |
| Notional | ${notional:,.0f} |
| Order ID | {order_id} |
| Rule(s) | {rule} |
| Regime | {regime} |
| Price (est.) | {"N/A" if price_est is None else f"${price_est:,.2f}"} |
| Dry run | {"YES" if dry_run else "NO"} |
"""
    path.write_text(content, encoding="utf-8")
    print(f"  Decision logged → {fname}")


def update_positions(dry_run: bool) -> None:
    if dry_run:
        print("  [dry-run] Skipping positions.md update.")
        return

    positions = alpaca.get_positions()
    acct = alpaca.get_account()
    today = date.today().isoformat()
    path = ROOT / "memory" / "positions.md"

    lines = [
        "# Current Paper Positions\n",
        "\n",
        "> Source of truth for open Alpaca paper positions.\n",
        "> Updated by every routine that changes positions (market-open, midday, EOD).\n",
        "> Never manually edit — only routines write here.\n",
        "\n",
        f"Last updated: {today} (market-open routine)\n",
        "\n",
        "---\n",
        "\n",
    ]

    if not positions:
        lines.append("## Open positions\n\n*(None — fully in cash)*\n\n")
    else:
        lines.append("## Open positions\n\n")
        lines.append("| Ticker | Shares | Avg cost | Current price | Market value | % of equity | Entry date | Regime at entry |\n")
        lines.append("|--------|--------|----------|---------------|--------------|-------------|------------|------------------|\n")
        for p in positions:
            pct = p["market_value"] / acct.equity * 100 if acct.equity else 0
            lines.append(
                f"| {p['ticker']} | {p['qty']:.4f} | ${p['avg_cost']:,.2f} | "
                f"${p['current_price']:,.2f} | ${p['market_value']:,.2f} | "
                f"{pct:.1f}% | {today} | — |\n"
            )

    lines.append(f"\n## Account summary\n\n")
    lines.append(f"| Field | Value |\n|-------|-------|\n")
    lines.append(f"| Equity | ${acct.equity:,.2f} |\n")
    lines.append(f"| Cash | ${acct.cash:,.2f} |\n")
    lines.append(f"| Buying power | ${acct.buying_power:,.2f} |\n")

    path.write_text("".join(lines), encoding="utf-8")
    print(f"  positions.md updated.")


def main(dry_run: bool) -> None:
    today = date.today().isoformat()
    now_et = datetime.now(ET)
    print(f"\n=== Market-Open Routine — {today} {now_et.strftime('%H:%M ET')} ===")
    if dry_run:
        print("  [DRY RUN — no real orders will be placed]\n")

    data = load_proposals(today)

    if not data.get("confirmed"):
        print("Regime not confirmed. No trades today per Rule 3.1.")
        sys.exit(0)

    proposals = data.get("proposals", [])
    if not proposals:
        print("No actionable proposals in today's file.")
        sys.exit(0)

    regime = data.get("regime", "UNKNOWN")
    acct = alpaca.get_account()
    print(f"Account: equity=${acct.equity:,.2f}  cash=${acct.cash:,.2f}\n")

    orders_placed = 0
    for prop in proposals:
        ticker = prop["ticker"]
        side = prop["side"]
        notional = float(prop["notional"])
        rule = prop.get("rule", "—")

        print(f"  Checking {side.upper()} {ticker} ${notional:,.0f} …")

        checks = run_checks(
            ticker=ticker,
            side=side,
            notional=notional,
            portfolio_equity=acct.equity,
            cash=acct.cash,
            daily_order_count=orders_placed,
        )

        failed = [c for c in checks if not c.passed]
        if failed:
            for c in failed:
                print(f"    BLOCKED [{c.check}]: {c.reason}")
            continue

        if dry_run:
            print(f"    [dry-run] Would place {side.upper()} {ticker} ${notional:,.0f}")
            log_decision(ticker, side, notional, "DRY-RUN", rule, regime, None, dry_run=True)
            orders_placed += 1
            continue

        order = alpaca.place_market_order(ticker, side, notional)
        print(f"    ORDER PLACED: {order['id']} status={order['status']}")
        log_decision(ticker, side, notional, order["id"], rule, regime, None, dry_run=False)
        orders_placed += 1

    print(f"\n{orders_placed} order(s) placed.")
    update_positions(dry_run)
    print("\nMarket-open routine complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate and log without placing real orders")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
