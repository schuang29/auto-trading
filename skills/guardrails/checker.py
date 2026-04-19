"""
Order guardrail checker. Validates a proposed order against all hard limits.
Reads strategy/universe.md and guardrails/ files at runtime.

Usage:
    python skills/guardrails/checker.py --ticker VTI --side buy --notional 5000 \
        --portfolio-equity 100000 --cash 10000 --daily-order-count 1

Returns exit code 0 if the order passes all checks, 1 if any check fails.
Prints a structured result to stdout.
"""
import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]

ET = ZoneInfo("America/New_York")
MARKET_OPEN = (9, 30)
MARKET_CLOSE = (16, 0)
MAX_POSITION_PCT = 0.30
MIN_ORDER_NOTIONAL = 500.0
MAX_DAILY_ORDERS = 5
MIN_CASH_BUFFER_PCT = 0.05
MIN_HOLDING_DAYS = 30


@dataclass
class CheckResult:
    passed: bool
    check: str
    reason: str


def _load_universe() -> set[str]:
    path = ROOT / "strategy" / "universe.md"
    text = path.read_text(encoding="utf-8")
    # Extract ticker symbols from markdown table rows: | TICKER |
    return set(re.findall(r"\|\s*([A-Z]{2,5})\s*\|", text))


def _load_restricted() -> set[str]:
    path = ROOT / "guardrails" / "restricted.md"
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"\|\s*([A-Z]{2,5})\s*\|", text))


def _load_blackout_dates() -> set[date]:
    path = ROOT / "guardrails" / "blackouts.md"
    text = path.read_text(encoding="utf-8")
    found = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
    return {date.fromisoformat(d) for d in found}


def run_checks(
    ticker: str,
    side: str,
    notional: float,
    portfolio_equity: float,
    cash: float,
    daily_order_count: int,
    holding_days: int | None = None,
) -> list[CheckResult]:
    results = []
    today = date.today()
    now_et = datetime.now(ET)

    # 1. Blackout dates
    blackouts = _load_blackout_dates()
    results.append(CheckResult(
        passed=today not in blackouts,
        check="blackout_dates",
        reason="OK" if today not in blackouts else f"{today} is a blackout date",
    ))

    # 2. Market hours (ET)
    open_h, open_m = MARKET_OPEN
    close_h, close_m = MARKET_CLOSE
    market_open = now_et.hour * 60 + now_et.minute >= open_h * 60 + open_m
    market_close = now_et.hour * 60 + now_et.minute <= close_h * 60 + close_m
    in_hours = market_open and market_close
    results.append(CheckResult(
        passed=in_hours,
        check="market_hours",
        reason="OK" if in_hours else f"Outside market hours (ET {now_et.strftime('%H:%M')})",
    ))

    # 3. Whitelist
    universe = _load_universe()
    on_whitelist = ticker in universe
    results.append(CheckResult(
        passed=on_whitelist,
        check="whitelist",
        reason="OK" if on_whitelist else f"{ticker} not in strategy/universe.md",
    ))

    # 4. Restricted list
    restricted = _load_restricted()
    not_restricted = ticker not in restricted
    results.append(CheckResult(
        passed=not_restricted,
        check="restricted_list",
        reason="OK" if not_restricted else f"{ticker} is on guardrails/restricted.md",
    ))

    # 5. Max position size (buy only)
    if side == "buy":
        projected_position = notional
        pct = projected_position / portfolio_equity if portfolio_equity > 0 else 1.0
        under_cap = pct <= MAX_POSITION_PCT
        results.append(CheckResult(
            passed=under_cap,
            check="max_position_size",
            reason="OK" if under_cap else f"Order is {pct:.1%} of equity; max is {MAX_POSITION_PCT:.0%}",
        ))
    else:
        results.append(CheckResult(passed=True, check="max_position_size", reason="N/A (sell)"))

    # 6. Min order size
    above_min = notional >= MIN_ORDER_NOTIONAL
    results.append(CheckResult(
        passed=above_min,
        check="min_order_size",
        reason="OK" if above_min else f"Notional ${notional:.0f} below minimum ${MIN_ORDER_NOTIONAL:.0f}",
    ))

    # 7. Daily order count
    under_limit = daily_order_count < MAX_DAILY_ORDERS
    results.append(CheckResult(
        passed=under_limit,
        check="daily_order_count",
        reason="OK" if under_limit else f"Already placed {daily_order_count} orders today (max {MAX_DAILY_ORDERS})",
    ))

    # 8. Cash buffer (buy only)
    if side == "buy":
        cash_after = cash - notional
        buffer_pct = cash_after / portfolio_equity if portfolio_equity > 0 else 0
        has_buffer = buffer_pct >= MIN_CASH_BUFFER_PCT
        results.append(CheckResult(
            passed=has_buffer,
            check="cash_buffer",
            reason="OK" if has_buffer else f"Cash after fill would be {buffer_pct:.1%}; minimum is {MIN_CASH_BUFFER_PCT:.0%}",
        ))
    else:
        results.append(CheckResult(passed=True, check="cash_buffer", reason="N/A (sell)"))

    # 9. Holding period (sell only)
    if side == "sell" and holding_days is not None:
        meets_hold = holding_days >= MIN_HOLDING_DAYS
        results.append(CheckResult(
            passed=meets_hold,
            check="holding_period",
            reason="OK" if meets_hold else f"Position held {holding_days}d; minimum is {MIN_HOLDING_DAYS}d",
        ))
    else:
        results.append(CheckResult(passed=True, check="holding_period", reason="N/A"))

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a proposed order against all guardrails")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--side", required=True, choices=["buy", "sell"])
    parser.add_argument("--notional", required=True, type=float)
    parser.add_argument("--portfolio-equity", required=True, type=float)
    parser.add_argument("--cash", required=True, type=float)
    parser.add_argument("--daily-order-count", required=True, type=int)
    parser.add_argument("--holding-days", type=int, default=None)
    args = parser.parse_args()

    results = run_checks(
        ticker=args.ticker,
        side=args.side,
        notional=args.notional,
        portfolio_equity=args.portfolio_equity,
        cash=args.cash,
        daily_order_count=args.daily_order_count,
        holding_days=args.holding_days,
    )

    all_passed = all(r.passed for r in results)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.check}: {r.reason}")

    print(f"\nResult: {'ORDER APPROVED' if all_passed else 'ORDER REJECTED'}")
    sys.exit(0 if all_passed else 1)
