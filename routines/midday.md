# Midday Routine

**Schedule:** Weekdays 12:30 PM ET
**Purpose:** Intraday position check — update high-water marks, flag trailing stop breaches, note large movers. No new orders placed.
**Execution:** Output goes to console and memory/daily/. Trailing stop alerts are queued for tomorrow's market-open.

---

## Instructions

You are the autonomous ETF trading bot for this project. Follow these steps exactly, in order. Do not skip steps. Do not place any orders.

### Step 1 — Fetch intraday position data

Run the midday data helper to get current prices, update high-water marks, and check trailing stops:

```bash
python scripts/midday.py
```

Parse the JSON output. Record:
- Each open position: ticker, current price, intraday P&L ($ and %), % from high-water mark
- Any trailing stop alerts (positions down 15%+ from HWM)
- Any large movers (positions up or down 2%+ intraday)

If the script fails, log the failure and proceed with any available data. Note Rule 7.2.

### Step 2 — Check trailing stop alerts

Review `trailing_stop_alerts` from the output.

- If **no alerts**: note "No trailing stops triggered."
- If **alerts exist**: flag each triggered position:

```
TRAILING STOP TRIGGERED (MIDDAY): [TICKER]
  Current price: $X.XX
  High-water mark: $X.XX
  Drawdown from HWM: -X.X%
  Action required: EXIT [TICKER] at market open tomorrow per Rule 5.2
```

These alerts must appear in the daily log. The EOD routine will also check stops; midday detection gives an earlier warning.

### Step 3 — Note large movers

For any ticker in `large_movers` (intraday move >= 2%):
- If the move is **against** the position (down for a long), note the cause if known.
- Use a targeted web search only if a position is down >3% intraday — search `[TICKER] stock news today`.
- Otherwise skip the web search to keep this routine fast.

### Step 4 — Log to memory

Append a brief midday check to today's daily log:

```bash
python skills/memory/logger.py --type daily --content "
## Midday Check

**Time:** [HH:MM ET]
**Account:** $[equity] | Cash: $[cash]

**Positions:**
[one line per position: TICKER  current_price  intraday_pl%  pct_from_hwm]

**Trailing stop alerts:** [count] ([list tickers or 'none'])
**Large movers:** [list or 'none']
"
```

### Step 5 — Output summary to console

Print the midday brief. End with:

```
Midday check complete. Positions: [N]. Trailing stop alerts: [N].
Next: EOD routine at 4:15 PM ET.
```

---

## What NOT to do

- Do not place any orders. Trailing stop exits happen at the next market-open.
- Do not update memory/positions.md — that is EOD's responsibility.
- Do not run a full web search unless a position is down >3% intraday.
- Do not modify memory/decisions/ — midday creates no decision records.
