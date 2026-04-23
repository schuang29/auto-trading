"""
Alpaca paper trading client. All operations target the paper endpoint — never live.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

load_dotenv()


def _client() -> TradingClient:
    return TradingClient(
        os.environ["ALPACA_API_KEY"],
        os.environ["ALPACA_SECRET_KEY"],
        paper=True,
    )


@dataclass
class AccountState:
    equity: float
    cash: float
    buying_power: float


def get_account() -> AccountState:
    acct = _client().get_account()
    return AccountState(
        equity=float(acct.equity),
        cash=float(acct.cash),
        buying_power=float(acct.buying_power),
    )


def get_positions() -> list[dict]:
    """Return current positions as a list of dicts."""
    positions = _client().get_all_positions()
    return [
        {
            "ticker": p.symbol,
            "qty": float(p.qty),
            "avg_cost": float(p.avg_entry_price),
            "market_value": float(p.market_value),
            "current_price": float(p.current_price),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_intraday_pl": float(p.unrealized_intraday_pl),
            "unrealized_intraday_plpc": float(p.unrealized_intraday_plpc),
        }
        for p in positions
    ]


def place_market_order(ticker: str, side: str, notional: float) -> dict:
    """
    Submit a notional market order. Returns order details as a dict.
    side must be 'buy' or 'sell'.
    """
    req = MarketOrderRequest(
        symbol=ticker,
        notional=round(notional, 2),
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    order = _client().submit_order(req)
    return {
        "id": str(order.id),
        "ticker": order.symbol,
        "side": side,
        "notional": notional,
        "status": str(order.status),
    }


def cancel_order(order_id: str) -> None:
    _client().cancel_order_by_id(order_id)


def get_open_orders() -> list[dict]:
    req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
    orders = _client().get_orders(req)
    return [
        {
            "id": str(o.id),
            "ticker": o.symbol,
            "side": str(o.side),
            "status": str(o.status),
            "notional": float(o.notional) if o.notional else None,
        }
        for o in orders
    ]
