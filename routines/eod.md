# End-of-Day Routine

**Schedule:** Weekdays 4:15 PM ET
**Purpose:** Snapshot end-of-day P&L, check trailing stops, write daily close summary to memory.
**Execution:** No new orders are placed. Trailing stop alerts are written to memory for the pre-market routine to act on tomorrow.

---

## Instructions

You are the autonomous ETF trading bot for this project. Follow these steps exactly, in order. Do not skip steps. Do not place any orders.

### Step 1 — Fetch positions and P&L

Run the EOD data helper to get current Alpaca paper positions, compute P&L, check trailing stops, and update `memory/positions.md` and `memory/highwatermarks.json`:

```bash
python scripts/eod.py
```

Parse the JSON output. Record:
- Total portfolio value and unrealized P&L ($ and %)
- Each open position: ticker, market value, unrealized P&L, % from high-water mark
- Any trailing stop alerts (positions down 15%+ from high-water mark)

If the script fails (e.g., Alpaca API error), log the failure and proceed with the remaining steps using whatever data is available. Note Rule 7.2: do not attempt trades if the API is erroring.

### Step 2 — Check trailing stop alerts

Review `trailing_stop_alerts` from the eod.py output.

- If **no alerts**: note "No trailing stops triggered."
- If **alerts exist**: for each triggered ticker, write a clear flag:

```
TRAILING STOP TRIGGERED: [TICKER]
  Current price: $X.XX
  High-water mark: $X.XX
  Drawdown from HWM: -X.X%
  Action required: EXIT [TICKER] at market open tomorrow per Rule 5.2
```

These alerts must appear prominently in the daily log so the market-open routine sees them.

### Step 3 — Market close context

Use web search to retrieve a brief market close summary:

**Search 1:** `S&P 500 close today [date] stock market`
Record: final S&P 500 close level and day change ($ and %).

**Search 2:** `10 year treasury yield close today [date]`
Record: 10-year yield close.

**Search 3 (if any position is down >2% today):** Search for news on that specific ETF.

Write a 3–5 bullet summary of the market close relevant to the portfolio.

### Step 4 — Assess regime consistency

Compare today's closing data against this morning's regime signals (read from today's `memory/daily/` pre-market entry):
- Is the regime still consistent with the pre-market read? Note any divergence.
- Were any proposed trades that went unexecuted today still valid at close?

### Step 5 — Log to memory

Append the EOD summary to today's daily log:

```bash
python skills/memory/logger.py --type daily --content "
## EOD Summary

**Portfolio:** $[equity] | P&L today: $[unrealized_pl] ([unrealized_pl_pct]%) | Cash: [cash_pct]%

**Positions:**
[one line per position: TICKER  market_value  unrealized_pl  pct_from_hwm]

**Trailing stop alerts:** [count] ([list tickers or 'none'])

**Market close:**
[bullet points]

**Regime check:** [still consistent / diverging — detail]
"
```

### Step 6 — Output summary to console

Print the full EOD brief. End with:

```
EOD routine complete. Positions: [N]. Trailing stop alerts: [N].
Next: pre-market routine tomorrow at 7:30 AM ET.
```

---

## What NOT to do

- Do not place any orders. Trailing stop alerts are logged for tomorrow's market-open.
- Do not modify `memory/decisions/` — EOD does not create decision records.
- Do not alter the regime classification — that is the pre-market routine's job.
- Do not hallucinate position data. If eod.py fails, note the failure and use "data unavailable."
