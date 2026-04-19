# Runbook — Operating the Trading Bot

> How to run, monitor, debug, and manage the bot in its current state.
> Update this file as new routines and phases come online.

---

## Scheduled agents

### Pre-market routine

| Field | Value |
|-------|-------|
| Trigger ID | `trig_01Wr6G75gDj6RuuwcfJMnktE` |
| Schedule | Weekdays 7:30 AM ET (cron: `30 11 * * 1-5` UTC) |
| Model | `claude-sonnet-4-6` |
| Repo | `https://github.com/schuang29/auto-trading` |
| Created | 2026-04-19 |
| Manage | https://claude.ai/code/scheduled/trig_01Wr6G75gDj6RuuwcfJMnktE |

**What it does:** Follows `routines/pre_market.md` — fetches regime signals (SPY trend, VIX, yield curve), classifies the regime, reads strategy files, drafts trade proposals, writes a market context summary, logs everything to `memory/daily/YYYY-MM-DD.md`, and pushes the log to GitHub.

**DST caveat:** The cron is fixed at `30 11 * * 1-5` UTC. This equals 7:30 AM EDT (summer) but 6:30 AM EST (winter). Update the cron in November when clocks fall back:
- Summer (EDT, UTC-4): `30 11 * * 1-5`
- Winter (EST, UTC-5): `30 12 * * 1-5`

Update via Claude Code: *"Update the pre-market scheduled agent cron to `30 12 * * 1-5`"*

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
2. Check `memory/daily/run-log-YYYY-MM-DD.txt` if it exists (future: added when shell wrapper is in place).
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
