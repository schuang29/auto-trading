"""Phase 0 connectivity check — prints Alpaca paper account info and exits."""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

api_key = os.environ["ALPACA_API_KEY"]
secret_key = os.environ["ALPACA_SECRET_KEY"]

client = TradingClient(api_key, secret_key, paper=True)
account = client.get_account()

print("Alpaca paper account connected.")
print(f"  Status:      {account.status}")
print(f"  Equity:      ${float(account.equity):,.2f}")
print(f"  Cash:        ${float(account.cash):,.2f}")
print(f"  Buying power: ${float(account.buying_power):,.2f}")
