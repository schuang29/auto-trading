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

**Registered.** All scheduled tasks (including EOD) are live — see "All
scheduled tasks" below. They are (re)registered together by
`scripts/setup_scheduler.ps1`, which must be run **as Administrator**.

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

The bot runs via **Windows Task Scheduler**, not a cloud scheduler. To pause
all automated runs, disable the tasks (PowerShell as Administrator):

```powershell
Get-ScheduledTask -TaskName "AutoTrading-*" | Disable-ScheduledTask
```

Re-enable with `Enable-ScheduledTask`. No code changes needed. Note: while
disabled, the heartbeat is also off, so a disabled bot will not self-alert —
disabling is a deliberate operator action, not a failure.

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

## All scheduled tasks

All registered together by `scripts/setup_scheduler.ps1` (run **as
Administrator**). All share battery-safe settings (see Reliability below).

| Task | Schedule (ET) | Wrapper |
|------|---------------|---------|
| `AutoTrading-PreMarket` | Weekdays 7:30 AM | `run_pre_market.ps1` |
| `AutoTrading-MarketOpen` | Weekdays 9:35 AM | `run_market_open.ps1` |
| `AutoTrading-Midday` | Weekdays 12:30 PM | `run_midday.ps1` |
| `AutoTrading-EOD` | Weekdays 4:15 PM | `run_eod.ps1` |
| `AutoTrading-Weekly` | Fridays 5:00 PM | `run_weekly.ps1` |
| `AutoTrading-Heartbeat` | Weekdays 6:30 PM | `run_heartbeat.ps1` |

---

## Reliability (added after the W20 incident, 2026-05-17)

Full post-mortem: `memory/health/2026-W20-reliability-incident.md`,
`memory/weekly/2026-W20.md`. ADRs: `docs/decisions/0007-*`, `0008-*`.

### Battery lockout — the root cause of the 3-day void

`New-ScheduledTaskSettingsSet` defaults `DisallowStartIfOnBatteries=$true` and
`StopIfGoingOnBatteries=$true`. On battery, every task silently skips and
`NumberOfMissedRuns` stays 0 (scheduler looks healthy while the bot is dark).
`setup_scheduler.ps1` now clears both on the shared settings object.

> **Required after any change here:** re-run `setup_scheduler.ps1` **as
> Administrator**. Modifying the already-registered `RunLevel Highest` tasks
> needs elevation (`Set-ScheduledTask` is otherwise access-denied), so the
> live tasks keep the old setting until this is done.

### Headless git push (the audit trail must reach origin)

The scheduled context cannot use the Windows Credential Manager. Setup:

1. Create a GitHub **fine-grained PAT**, this repo only, Contents: Read and
   write.
2. Put it in `.env` as `GITHUB_TOKEN=...` (gitignored; never commit it).

`scripts/git-credential-env.sh` feeds that token to git for `get` only (silent
otherwise, so interactive use still works). `scripts/sync_git.ps1` runs at the
end of every wrapper: it rebuilds the credential chain idempotently, pushes,
verifies `origin/main..HEAD == 0`, and on failure writes a committed
`memory/health/PUSH-FAILED-*.md`, emails, and exits non-zero.

### Dead-man's-switch

`AutoTrading-Heartbeat` (18:30 ET weekdays) runs `scripts/heartbeat.py`: it
verifies recent trading days each have a `portfolio_daily.csv` row + an EOD
section and that the audit trail reached origin. On a miss: committed
`memory/health/ALERT-*.md`, SMTP email, non-zero exit. To stop a *known* outage
from re-alerting, add a `RELIABILITY GAP` / `NO ROUTINE RAN` marker to that
day's `memory/daily/*.md` (see the 2026-05-13..15 markers for the format).

Email alerts need `SMTP_HOST/PORT/USER/PASS` + `NOTIFY_EMAIL_TO` in `.env`
(Gmail: use an App Password, port 587). Until set, alerts are still durable
locally and as non-zero exits.

### Operator checklist after a host change / new machine

1. `.env` present with `GITHUB_TOKEN` + `SMTP_*` filled in.
2. Run `setup_scheduler.ps1` as Administrator; confirm all six tasks
   `Ready` and `DisallowStartIfOnBatteries=False`.
3. Trigger `AutoTrading-PreMarket` once manually; confirm a
   `portfolio_daily.csv`/daily-log update and a clean `origin/main` push.
