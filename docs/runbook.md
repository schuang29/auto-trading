# Runbook — Operating the Trading Bot

> How to run, monitor, debug, and manage the bot in its current state.
> Update this file as new routines and phases come online.

---

## Scheduled tasks

### Pre-market routine

| Field | Value |
|-------|-------|
| Task name | `AutoTrading-PreMarket` |
| Schedule | Weekdays 7:30 AM ET |
| Model | `claude-opus-4-7` |
| Wrapper script | `scripts/run_pre_market.ps1` |
| Setup script | `scripts/setup_scheduler.ps1` (run once as Administrator) |
| Log file | `logs/pre_market_YYYY-MM-DD.log` (local only, gitignored) |
| Created | 2026-04-19 |
| Manage | Task Scheduler (`taskschd.msc`) → Task Scheduler Library → `AutoTrading-PreMarket` |

**What it does:** Follows `routines/pre_market.md` — fetches regime signals (SPY trend, VIX, yield curve), classifies the regime, reads strategy files, drafts trade proposals, writes a market context summary, logs everything to `memory/daily/YYYY-MM-DD.md`, and pushes the log to GitHub.

**DST caveat:** Windows Task Scheduler uses local time, so 7:30 AM ET is always correct across daylight saving transitions. No manual adjustment needed.

**Re-registering the task** (if ever needed — run PowerShell as Administrator):
```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\setup_scheduler.ps1"
```

### EOD routine

| Field | Value |
|-------|-------|
| Task name | `AutoTrading-EOD` |
| Schedule | Weekdays 4:15 PM ET (starting 2026-04-27) |
| Model | `claude-sonnet-4-6` |
| Wrapper script | `scripts/run_eod.ps1` |
| Log file | `logs/eod_YYYY-MM-DD.log` (local only, gitignored) |

**What it does:** Runs `scripts/eod.py` to fetch Alpaca paper positions, compute unrealized P&L, update high-water marks in `memory/highwatermarks.json`, check trailing stops (Rule 5.2 — 15% from HWM), update `memory/positions.md`, fetch market close context via web search, then appends an EOD summary to today's `memory/daily/` log.

**Trailing stop alerts:** Any position down 15%+ from its high-water mark is flagged in the daily log. The pre-market routine reads this and generates an exit proposal for the following morning.

**To run manually:**
```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_eod.ps1"
```

**To register in Task Scheduler** (run PowerShell as Administrator — not yet done):
```powershell
# Register AutoTrading-EOD task pointing to run_eod.ps1, weekdays 4:15 PM ET
```

---

### Market-open routine

| Field | Value |
|-------|-------|
| Task name | `AutoTrading-MarketOpen` |
| Schedule | Weekdays 9:35 AM ET (starting 2026-04-27) |
| Wrapper script | `scripts/run_market_open.ps1` |
| Log file | `logs/market_open_YYYY-MM-DD.log` (local only, gitignored) |
| Created | 2026-04-21 |
| Manage | Task Scheduler (`taskschd.msc`) → Task Scheduler Library → `AutoTrading-MarketOpen` |

**What it does:** Reads today's proposals from `memory/proposals/YYYY-MM-DD.json` (written by the pre-market routine), runs each through the guardrail checker, places approved notional market orders on Alpaca paper, logs every trade to `memory/decisions/`, updates `memory/positions.md`, and commits to GitHub.

**Dependency:** The pre-market routine must complete first and write the proposals JSON. If the file is missing, the market-open script aborts cleanly with an error.

---

## Running a routine manually (ad-hoc)

If your PC was off at the scheduled time, or you want to run outside the schedule:

### Pre-market (fetch signals + write proposals)

Option 1 — Run the wrapper script directly:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_pre_market.ps1"
```

Option 2 — Trigger from Task Scheduler GUI: open `taskschd.msc` → find `AutoTrading-PreMarket` → right-click → **Run**.

**Timing note:** Run after 7:00 AM ET for reliable VIX and futures data. Running earlier means slightly stale pre-market readings.

### Market-open (execute proposals on Alpaca)

Only run this after the pre-market routine has completed and `memory/proposals/YYYY-MM-DD.json` exists.

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_market_open.ps1"
```

Or trigger from Task Scheduler GUI: find `AutoTrading-MarketOpen` → right-click → **Run**.

**Timing note:** Best run during market hours (9:30 AM–4:00 PM ET). The guardrail checker will block orders outside market hours. If you missed the window entirely, skip that day — do not force after-hours execution.

### Dry-run (validate without placing orders)

To test the market-open flow without touching Alpaca:
```powershell
.venv\Scripts\python.exe scripts\market_open.py --dry-run
```

---

## Checking routine output

Each run appends to `memory/daily/YYYY-MM-DD.md`. To check what the bot did this morning:

```bash
cat memory/daily/$(date +%Y-%m-%d).md
```

Or open the file in VS Code. The file includes the regime classification, proposed trades, and market context summary.

---

## Disabling the bot

To pause all automated runs: https://claude.ai/code/scheduled

Toggle the `pre-market-routine` trigger off. No code changes needed.

---

## Debugging a failed run

1. Check `memory/daily/YYYY-MM-DD.md` — the routine logs failures inline and continues.
2. Check `logs/pre_market_YYYY-MM-DD.log` — the wrapper script logs every step including errors and the Claude exit code.
3. Common failure modes:
   - **yfinance timeout** — transient; next run will recover. No action needed.
   - **FRED API down** — yield curve signal skipped; two-signal majority vote still works.
   - **Git push failed** — daily log not persisted; check repo permissions.
   - **Regime not confirmed** — expected behavior on day 1 of a regime change. Not a failure.

---

## Adding future routines

When Phase 3+ routines are ready, create additional scheduled tasks following the same pattern as the two existing ones:

| Routine | Status | Suggested schedule (ET) |
|---------|--------|------------------------|
| Pre-market | Live (`AutoTrading-PreMarket`) | Weekdays 7:30 AM |
| Market open | Live (`AutoTrading-MarketOpen`) | Weekdays 9:35 AM |
| Midday | Not yet built | Weekdays 12:30 PM |
| End of day | Not yet built | Weekdays 4:15 PM |
| Weekly review | Not yet built | Fridays 5:00 PM |
