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
| Model | `claude-sonnet-4-6` |
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

---

## Checking routine output

Each run appends to `memory/daily/YYYY-MM-DD.md`. To check what the bot did this morning:

```bash
cat memory/daily/$(date +%Y-%m-%d).md
```

Or open the file in VS Code. The file includes the regime classification, proposed trades, and market context summary.

---

## Running a routine manually

To trigger the pre-market routine immediately (bypasses the schedule):

Option 1 — Run via Claude Code locally:
```
claude
> Follow the pre-market routine in routines/pre_market.md
```

Option 2 — Trigger the remote agent now via Claude Code CLI:
*"Run the pre-market scheduled agent now"* (Claude Code will use the RemoteTrigger tool)

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

When Phase 3+ routines are ready, create additional scheduled agents following the same pattern:

| Routine | Suggested schedule (ET) | Cron (EDT/UTC-4) |
|---------|------------------------|-----------------|
| Market open | Weekdays 9:35 AM | `35 13 * * 1-5` |
| Midday | Weekdays 12:30 PM | `30 16 * * 1-5` |
| End of day | Weekdays 4:15 PM | `15 20 * * 1-5` |
| Weekly review | Fridays 5:00 PM | `0 21 * * 5` |
