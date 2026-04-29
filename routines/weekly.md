# Weekly Review Routine

**Schedule:** Fridays 5:00 PM ET (after EOD)
**Purpose:** Compute weekly performance, assess regime accuracy, summarize trades, and propose strategy tweaks for human review. Does not auto-apply any changes.
**Execution:** Reads from `memory/daily/`, `memory/decisions/`, `memory/timeseries/`. Writes a single review file to `memory/weekly/`. No orders placed.

---

## Instructions

You are the autonomous ETF trading bot for this project. Follow these steps exactly, in order. Do not skip steps. Do not place any orders. Do not modify strategy files — propose changes for human review only.

### Step 0 — Determine the ISO week

Compute the ISO week number for today (Friday). The output filename is `memory/weekly/YYYY-Www.md` where `Www` is zero-padded (e.g. `2026-W18.md`). Use Python if helpful:

```bash
python -c "import datetime; d = datetime.date.today(); y, w, _ = d.isocalendar(); print(f'{y}-W{w:02d}')"
```

Record the year-week tag and the date range (Monday → Friday) for this week.

### Step 1 — Read the week's daily logs

Read every `memory/daily/YYYY-MM-DD.md` for the trading days in this ISO week (typically Monday–Friday, but may be 3–5 days if there were holidays). For each day extract:
- Pre-market regime call and confirmation status
- Number of trades executed at market-open
- Any trailing stop alerts (midday or EOD)
- EOD equity, daily P&L $ and %
- Any noted compliance flags or anomalies

If a day's log is missing entirely (routine failed), note it explicitly. A missed day is a Phase 4 reliability concern.

### Step 2 — Read the week's decision files

List all files in `memory/decisions/` with names matching this week's date range. For each:
- Ticker, side, notional, rule(s) cited
- Whether it was a real order or DRY-RUN

Aggregate:
- Total orders this week
- Total notional traded (buy + sell)
- Tickers touched
- Rules most frequently cited

### Step 3 — Compute performance from the time-series CSVs

Read `memory/timeseries/portfolio_daily.csv` and filter to rows in this week.

Compute:
- **Weekly return** — `(friday_equity / monday_open_equity) - 1`. Use Monday's row as the base; if Monday is missing, use the earliest available day this week.
- **Best day** — date and daily_pnl_pct
- **Worst day** — date and daily_pnl_pct
- **Cumulative since inception** — read the latest cumulative_pnl_pct column

Read `memory/timeseries/benchmarks_daily.csv` for the same date range. For each benchmark (SPY, AGG, VT, 60_40_BLEND), compute the same week-over-week return as above.

Compute **alpha vs 60/40** for the week: `bot_weekly_return - blend_60_40_weekly_return`.

If a CSV is missing or the week's data is incomplete, note exactly what is unavailable. Do not fabricate numbers.

### Step 4 — Assess regime accuracy

For each day's recorded regime (from Step 1), check whether the regime call held through the day or was contradicted by EOD market action.

Specifically:
- Did the regime classification flip during the week? If so, when, and was it confirmed?
- Were there days where the regime said RISK-ON but SPY closed down >1% (or RISK-OFF but SPY closed up >1%)? Note these as "regime tension" days — not necessarily wrong, but worth tracking over time.

This is an honest scoring exercise, not advocacy. The bot's value depends on regime calls being useful.

### Step 5 — Identify proposed strategy adjustments (read-only)

Based on the week's observations, propose any strategy adjustments. Examples:
- A target weight that consistently feels wrong
- A rule that produced a counterintuitive trade
- A ticker that should be added to or removed from the curated shortlist
- A guardrail threshold that triggered too often or never

**Important:** Do NOT modify any file in `strategy/`, `guardrails/`, or `routines/`. Only WRITE the proposals into the weekly review file. The user reviews and decides whether to apply.

If no changes are warranted, write "No strategy adjustments proposed this week."

### Step 6 — Write the weekly review file

Create `memory/weekly/YYYY-Www.md` with this structure:

```markdown
# Weekly Review — YYYY-Www
**Date range:** YYYY-MM-DD (Mon) → YYYY-MM-DD (Fri)
**Generated:** YYYY-MM-DD HH:MM ET

---

## Headline

[1-2 sentence summary: portfolio change, regime calls, anything notable]

## Performance

| Metric | Value |
|---|---|
| Bot weekly return | X.XX% |
| SPY weekly return | X.XX% |
| AGG weekly return | X.XX% |
| 60/40 blend weekly return | X.XX% |
| Alpha vs 60/40 | +/-X.XX pp |
| Bot cumulative since inception | X.XX% |
| Best day | YYYY-MM-DD (+X.XX%) |
| Worst day | YYYY-MM-DD (-X.XX%) |

If any benchmark or portfolio data was unavailable, note it explicitly here.

## Regime activity

- Monday: [regime, confirmed Y/N, notes]
- Tuesday: [regime, confirmed Y/N, notes]
- Wednesday: [regime, confirmed Y/N, notes]
- Thursday: [regime, confirmed Y/N, notes]
- Friday: [regime, confirmed Y/N, notes]

**Regime flips this week:** [count, with detail]
**Regime tension days:** [count, with detail]

## Trading activity

- **Orders placed:** N (notional $X)
- **Tickers touched:** [list]
- **Most-cited rules:** [Rule 4.2 (xN), Rule 3.1 (xN), ...]
- **Trailing stop alerts:** N ([list or "none"])
- **Dry-run / test orders:** N (excluded from real activity counts)

## Routine health

| Routine | Days expected | Days completed | Missed |
|---|---|---|---|
| Pre-market | N | N | [list dates or "none"] |
| Market-open | N | N | [list dates or "none"] |
| Midday | N | N | [list dates or "none"] |
| EOD | N | N | [list dates or "none"] |

If any routine missed a day, note the inferred cause (PC off, manual override, error).

## Compliance / anomalies

[Any flags raised in daily logs this week — e.g., the VIG/DGRO mismatch flag from earlier weeks. If none, write "None this week."]

## Proposed strategy adjustments (for human review — not applied)

[Numbered list, or "No strategy adjustments proposed this week." Each proposal cites the observation that triggered it.]

## Next week watch list

- Scheduled macro events (FOMC, CPI, PCE, NFP, earnings season weeks)
- Any unexecuted deferred trades from this week's pre-market briefings
- Any open trailing-stop watches (positions within 5% of stop)
```

### Step 7 — Output summary to console

Print a 6–10 line summary of the review file. End with:

```
Weekly review complete. File: memory/weekly/YYYY-Www.md
[N] proposed adjustments for review (or "No proposals this week.")
Next: pre-market routine Monday at 7:30 AM ET.
```

---

## What NOT to do

- Do not place any orders. Weekly review is read-only on positions.
- Do not modify any file in `strategy/`, `guardrails/`, or `routines/` — proposals only.
- Do not modify `memory/positions.md`, `memory/highwatermarks.json`, `memory/decisions/`, or `memory/timeseries/`.
- Do not retroactively rewrite earlier days' `memory/daily/` entries.
- Do not fabricate performance numbers if data is missing — say so plainly in the review.
- Do not run a deep backtest or optimization here. That belongs in Phase 6.
