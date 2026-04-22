# Pre-Market Routine

**Schedule:** Weekdays 7:30 AM ET
**Purpose:** Classify today's market regime and draft trade proposals for human review.
**Execution:** No orders are placed. Output goes to console and memory/daily/.

---

## Instructions

You are the autonomous ETF trading bot for this project. Follow these steps exactly, in order. Do not skip steps. Do not place any orders.

### Step 1 — Fetch regime signals

Use web search to retrieve each of the three signals. Search for current values — do not use cached or estimated data.

**Signal 1 — SPY trend:**
Search: `SPY current price and 200-day moving average`
Record: current price, 200-day SMA, and vote (risk-on if price > SMA, else risk-off).

**Signal 2 — VIX:**
Search: `VIX index current level`
Record: current VIX level and vote (risk-on if < 20, neutral if 20-25, risk-off if > 25).

**Signal 3 — Yield curve:**
Search: `US 10 year 2 year treasury yield spread today`
Record: spread in percentage points and vote (risk-on if > 0, neutral if 0 to -0.25, risk-off if < -0.25).

Apply majority vote across all three signals to determine the regime (RISK-ON / NEUTRAL / RISK-OFF).

If web search is unavailable, try running the local fetcher as a fallback:
```bash
python3 -m venv .venv 2>/dev/null; .venv/bin/pip install -r requirements.txt -q 2>/dev/null; .venv/bin/python skills/market_data/fetcher.py
```

If both methods fail, log the failure and classify regime as UNKNOWN. Do not guess.

### Step 2 — Check yesterday's regime

Read the most recent file in `memory/daily/` to find yesterday's regime classification. If no prior entry exists, treat today as day 1 of the current regime (not yet confirmed).

- If today's regime matches yesterday's regime: the regime is **confirmed**.
- If today's regime differs from yesterday's: this is **day 1** of a potential regime change. Note it but do not act on it today.

### Step 3 — Read current strategy files

Read the following files to ground your analysis:
- `strategy/universe.md` — approved ETF list
- `strategy/rules.md` — trading rules, especially the target allocations for the current regime
- `guardrails/hard_limits.md` — position caps and order limits
- `guardrails/blackouts.md` — confirm today is not a blackout date
- `memory/positions.md` — current paper positions (if it exists)

### Step 4 — Draft trade proposals

Based on the confirmed regime and current positions, identify any gaps between the current portfolio and the regime target allocation from `strategy/rules.md`.

For each proposed trade:
- State the ticker, side (buy/sell), approximate notional amount
- Cite the rule number from `strategy/rules.md` that justifies it
- Note the current holding period if it's a sell (Rule 3.4 / Rule 5.1)
- Flag any trade that cannot execute today (regime not confirmed, holding period not met, blackout)

Format:

```
PROPOSED TRADES (regime confirmed: YES/NO)
------------------------------------------
1. BUY VTI ~$X,XXX — Rule 3.1 (regime confirmed), Rule 2 (risk-on target 30%, current 0%)
2. BUY GLD ~$X,XXX — Rule 3.1, Rule 2 (inflation hedge, target 5%)
   [HOLD — regime not confirmed, wait for tomorrow]
```

If the regime is not confirmed, proposed trades should be listed but marked HOLD.

### Step 5 — Market context summary

Write a brief (3-5 bullet) summary of overnight conditions relevant to the portfolio:
- Any major macro news (central bank decisions, CPI/jobs data releases today)
- Futures direction (S&P, bond, gold)
- Any ETF in the universe with unusual pre-market movement

Use web search for current data. Cite sources inline.

### Step 6 — Log to memory

Append today's pre-market summary to the daily log using the memory logger:

```bash
python skills/memory/logger.py --type daily --content "
## Pre-Market Brief

**Regime:** [RISK-ON / NEUTRAL / RISK-OFF] (confirmed: YES/NO)
**Signals:**
- Trend: [detail]
- VIX: [detail]
- Yield curve: [detail]

**Proposed trades:** [count] ([count] on hold pending confirmation)
[list proposals]

**Market context:**
[bullet points]
"
```

### Step 7 — Write proposals JSON

Write a structured JSON file so the market-open script can execute without parsing markdown.
Only include proposals that are actionable today (regime confirmed, not marked HOLD).

Write to `memory/proposals/YYYY-MM-DD.json` (create the directory if it doesn't exist):

```bash
python -c "
import json, os
from datetime import date
from pathlib import Path

proposals = [
    # Fill in each actionable proposal as a dict:
    # {\"ticker\": \"VTI\", \"side\": \"buy\", \"notional\": 15000, \"rule\": \"3.1, 2\", \"priority\": 1},
]

data = {
    \"date\": date.today().isoformat(),
    \"regime\": \"[RISK-ON / NEUTRAL / RISK-OFF]\",
    \"confirmed\": True,  # or False if regime not confirmed
    \"proposals\": proposals,
}

path = Path('memory/proposals') / f'{date.today().isoformat()}.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(data, indent=2))
print(f'Proposals written to {path}')
"
```

If the regime is NOT confirmed, write the file with `\"confirmed\": false` and an empty `proposals` list.

### Step 8 — Output summary to console

Print the full pre-market brief so the user can review it. End with:

```
Pre-market routine complete. [N] trade proposals ready.
Next: run market-open routine at 9:35 AM ET if regime is confirmed.
```

---

## What NOT to do

- Do not place any orders. This routine is analysis only.
- Do not add tickers to the universe without user approval.
- Do not override the 2-day regime confirmation rule even if the signal looks obvious.
- Do not hallucinate market data. If a data fetch fails, note the failure and continue with the available signals.
