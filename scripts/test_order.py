"""
Connectivity and execution test. Places a 1-share VTI order on the paper account
and immediately cancels it. Run this once to confirm the plumbing works before Apr 25.

Usage:
    python scripts/test_order.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import skills.alpaca as alpaca
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


def main() -> None:
    print("=== Alpaca Paper Trading — Connectivity Test ===\n")

    acct = alpaca.get_account()
    print(f"Account connected.")
    print(f"  Equity:       ${acct.equity:,.2f}")
    print(f"  Cash:         ${acct.cash:,.2f}")
    print(f"  Buying power: ${acct.buying_power:,.2f}\n")

    print("Placing test order: BUY 1 share VTI …")

    # Use qty=1 (not notional) so we can place outside market hours too;
    # Alpaca accepts qty orders as GTC for paper even pre-market.
    from skills.alpaca import _client
    client = _client()
    req = MarketOrderRequest(
        symbol="VTI",
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
    order = client.submit_order(req)
    order_id = str(order.id)
    print(f"  Order placed: {order_id}  status={order.status}")

    print("Cancelling test order immediately …")
    try:
        alpaca.cancel_order(order_id)
        print(f"  Order {order_id} cancelled.")
    except Exception as e:
        print(f"  Cancel failed (may have already filled): {e}")
        print(f"  Cancel manually at https://app.alpaca.markets/paper-trading/orders")

    print("\nTest complete. Alpaca paper execution is working.")


if __name__ == "__main__":
    main()
