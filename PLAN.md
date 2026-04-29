# Autonomous ETF Trading Bot — Project Plan

> **Status:** Phase 0 complete — Sunday, April 19, 2026
> **Owner:** [you]
> **Scenario:** B (Fidelity for real execution, Alpaca paper for autonomy)

---

## 1. Goal

Build an autonomous, scheduled research-and-trading agent powered by Claude Code that:

1. Runs a disciplined ETF / bond-ETF strategy on **Alpaca paper trading** without human intervention.
2. Generates trade signals and rationale that the user manually executes in **Fidelity** (real money).
3. Respects employer compliance constraints (no individual stocks, ETF-only, possible whitelist).
4. Is fully version-controlled in a private GitHub repo with auditable decision history.

The bot is *not* a black box. Every trade or signal must include a human-readable rationale, and every routine writes to a markdown memory log so the user (and compliance, if asked) can reconstruct the "why" behind any decision.

---

## 2. Out of scope (for now)

- Trading individual stocks (compliance prohibits).
- Options, futures, crypto, leveraged/inverse ETFs.
- Direct Fidelity API automation (no public retail API exists; browser automation violates ToS and likely employer IT policy).
- Real-money execution by the bot itself. The bot is paper-only until further notice; real execution is human-in-the-loop in Fidelity.
- Tax-loss harvesting logic (out of scope for v1; revisit later).
- Multi-account or multi-user support.

---

## 3. Compliance constraints & open questions

The following must be confirmed with employer compliance before going live. The architecture is designed to work in the most restrictive plausible case so we are not blocked while waiting for answers.

| # | Question | Default assumption while waiting |
|---|---|---|
| 1 | Is **Alpaca** an approved broker for personal accounts (even paper trading)? | Assume yes for paper; confirm before any real-money use. |
| 2 | Does the ETF restriction require a **defined whitelist** or is any ETF allowed? | Build with a whitelist by default — easy to expand, hard to retrofit. |
| 3 | Are there **holding-period requirements** (e.g., 30/60-day minimum)? | Assume 30 days. Strategy will avoid frequent rotation. |
| 4 | Is there a **restricted ETF list** (sector ETFs touching employer industry, etc.)? | Build a `restricted.md` file the bot reads and refuses to trade. |
| 5 | Are **duplicate confirms / 407 letters** required? | Note for Fidelity setup; no impact on Alpaca paper. |
| 6 | Do **blackout windows** apply to ETF trades? | Build a `blackouts.md` file the bot honors. |

These live in `docs/compliance.md` in the repo and get updated as answers come in.

---

## 4. Tooling decisions

| Decision | Choice | Rationale |
|---|---|---|
| Editor | **VS Code** | User already has it; integrated terminal hosts Claude Code. |
| AI agent | **Claude Code CLI** (not Claude Desktop) | Built for agentic, autonomous, multi-step file/terminal/git work. Same tool the bot will use in production. |
| Model strategy | **`/model opusplan`** | Built-in hybrid: Opus 4.7 for planning, Sonnet 4.6 for execution. No manual switching needed. Manually `/model opus` for deep architecture sessions, `/model sonnet` for pure implementation. |
| Language | **Decided by Claude Code in Phase 0** based on Alpaca SDK quality, scheduling tools, and notification libraries. Likely Python (best Alpaca + finance ecosystem) but TypeScript is plausible. Documented in `docs/decisions/0001-language.md`. |
| Version control | **Git + private GitHub repo** | Required for auditability, secrets isolation, deploy targets later. |
| Secrets | **`.env` file (gitignored) + `1Password` or OS keychain for backup** | Never commit API keys. Document the required env vars in `.env.example`. |
| Scheduling (local dev) | **Built-in OS scheduler** (Task Scheduler on Windows / cron on macOS/Linux) | Free, simple, sufficient for paper trading. |
| Scheduling (later) | **Cloud cron** (GitHub Actions, Railway, or similar) | Decide in Phase 4. Nate Herk's video uses a cloud environment; we'll evaluate then. |
| Notifications (later) | **Email first, Slack optional** | Decide in Phase 5. |

### Why VS Code + Claude Code over Claude Desktop

Claude Desktop is a chat surface with MCP tool access — great for one-off questions and exploration, but you steer it more. Claude Code is purpose-built for agentic work: it edits files, runs commands, manages git, and operates with the autonomy needed for a real software project. Critically, it is also the runtime for the bot itself — once we're in production, the bot literally is Claude Code running on a schedule. Building in the same tool means no translation gap between "dev" and "prod."

---

## 5. Architecture

The architecture follows the model from Nate Herk's video, adapted for ETF-only and Scenario B (Alpaca paper + Fidelity manual).

### Five scheduled routines

| Routine | When | What it does |
|---|---|---|
| **Pre-market research** | Weekdays 7:30 AM ET | Pulls overnight news, futures, yield curve, VIX. Updates regime classification (risk-on / risk-off / neutral). Drafts proposed trades for the day. |
| **Market open** | Weekdays 9:35 AM ET | Reviews drafted trades against current prices. Executes on Alpaca paper. Generates Fidelity signal email/Slack. |
| **Midday scan** | Weekdays 12:30 PM ET | Checks open positions vs. stops and targets. Adjusts trailing stops if defined. |
| **End-of-day summary** | Weekdays 4:15 PM ET | Logs P&L, position changes, compares paper vs. expected Fidelity performance. Writes daily entry to memory log. |
| **Weekly review** | Fridays 5:00 PM ET | Computes weekly performance, regime accuracy, signal hit rate. Proposes strategy tweaks for human review (does not auto-apply). |

### Repo structure

```
.
├── README.md                   # Project overview, quick-start
├── PLAN.md                     # This document
├── CLAUDE.md                   # Instructions for Claude Code itself
├── .env.example                # Template for required secrets
├── .gitignore                  # Excludes .env, memory/private/, etc.
├── pyproject.toml or package.json
│
├── strategy/
│   ├── universe.md             # Approved ETF list (the whitelist)
│   ├── rules.md                # Entry/exit/sizing rules in plain English
│   ├── regimes.md              # Risk-on / risk-off classification logic
│   └── thesis.md               # Why this strategy is expected to work
│
├── guardrails/
│   ├── hard_limits.md          # Max position size, max trades/day, etc.
│   ├── restricted.md           # ETFs the bot must never trade
│   ├── blackouts.md            # Date ranges where no trading occurs
│   └── compliance.md           # Compliance rules in machine-readable form
│
├── routines/
│   ├── pre_market.md           # Prompt + procedure for pre-market routine
│   ├── market_open.md
│   ├── midday.md
│   ├── eod.md
│   └── weekly.md
│
├── skills/
│   ├── alpaca/                 # Wrapper functions for Alpaca paper API
│   ├── market_data/            # Yahoo Finance / Alpaca data wrapper
│   ├── notifications/          # Email / Slack senders
│   └── memory/                 # Read/write to memory logs
│
├── memory/
│   ├── decisions/              # One markdown file per trade decision
│   ├── daily/                  # YYYY-MM-DD.md daily logs
│   ├── weekly/                 # ISO-week summaries
│   └── positions.md            # Current paper position state
│
├── docs/
│   ├── compliance.md           # Open questions, answers as they arrive
│   ├── decisions/              # ADRs (architecture decision records)
│   └── runbook.md              # How to operate / debug the bot
│
└── tests/
    ├── guardrails_test.*       # Verify guardrails actually block bad trades
    └── routines_test.*         # Smoke tests for each routine
```

### Why markdown for strategy and memory

This is the key insight from Nate Herk's video: **the bot reads and writes its own memory and rules in markdown, not in a database**. The agent is a language model — markdown is its native format. Strategy rules in plain English are easier to write, easier to audit, and easier for the bot to follow correctly than JSON config or code. The bot reasons about the rules; it doesn't just execute them.

### Hard guardrails are code, not prompts

Soft guidance ("prefer broad-market ETFs") goes in markdown the bot reads. **Hard limits ("never trade more than 10% of portfolio in a single position") are enforced in code that gates every order before it reaches Alpaca.** A prompt can be ignored or misread; a Python `if` statement cannot. The guardrails layer is the safety net.

---

## 6. Phased milestones

### Phase 0 — Environment setup ✅ complete (April 19, 2026)

- [x] Install / update Claude Code CLI (`claude update`, confirm v2.1.111+ for Opus 4.7).
- [x] Create private GitHub repo `auto-trading`.
- [x] Clone locally, open in VS Code.
- [x] Create Alpaca paper trading account, generate API keys.
- [x] Create `.env` from `.env.example`, populate Alpaca paper keys.
- [x] Decide language: **Python** — best Alpaca SDK (`alpaca-py`), richest finance ecosystem (pandas, yfinance), mature scheduling and notification tooling. Documented in `docs/decisions/0001-language.md` (TODO).
- [x] Initial commit: `PLAN.md`, `CLAUDE.md`, `README.md`, `.gitignore`, `.env.example`, `requirements.txt`, `scripts/hello_alpaca.py`.
- [x] Verify Alpaca connection: `scripts/hello_alpaca.py` returned status ACTIVE, $100k equity.

**Exit criteria:** Met. Repo exists on GitHub, Alpaca paper account responds to API call, `claude` runs in the project directory.

### Phase 1 — Strategy & guardrails (no execution) ✅ complete (April 19, 2026)

- [x] Draft `strategy/universe.md` — 15 ETFs across US equity, intl equity, credit, treasuries, inflation hedges. Sector ETFs excluded pending compliance.
- [x] Draft `strategy/rules.md` — 8 rule groups: universe constraint, regime allocations, entry, sizing, exit, cash management, no-trade conditions, logging.
- [x] Draft `strategy/regimes.md` — three-signal classifier: SPY vs 200-day SMA, VIX level, 10yr-2yr yield curve spread. Majority vote, 2-day confirmation.
- [x] Draft `strategy/thesis.md` — why regime persistence justifies tactical allocation; falsification criteria defined.
- [x] Draft `guardrails/hard_limits.md` — 10-step sequential gate model; code enforcement in `skills/guardrails/` (Phase 2).
- [x] Write `guardrails/restricted.md` — empty pending compliance response.
- [x] Write `guardrails/blackouts.md` — NYSE holidays via Alpaca API; employer blackouts empty pending compliance.
- [x] Write `docs/compliance.md` — 6 open questions logged with default assumptions.
- [x] Write `docs/decisions/0001-language.md` — ADR documenting Python choice.
- [x] Write `CLAUDE.md` — committed in Phase 0.

**Exit criteria:** Met. A human can read strategy/ and guardrails/ and understand exactly what the bot will and won't do.

### Phase 2 — Single routine, automated via local Task Scheduler (in progress — April 19, 2026)

- [x] Implement `routines/pre_market.md` — full 7-step prompt: fetch signals, check prior regime, read strategy, draft proposals, market context, log to memory, print summary.
- [x] Implement `skills/market_data/fetcher.py` — pulls SPY 200d SMA (yfinance), VIX (yfinance), 10yr-2yr spread (FRED). Majority-vote regime classifier. Verified live: RISK-ON all three signals (2026-04-19).
- [x] Implement `skills/guardrails/checker.py` — 10-step sequential order gate. CLI-invokable. Reads universe/restricted/blackouts at runtime.
- [x] Implement `skills/memory/logger.py` — appends timestamped entries to memory/daily/YYYY-MM-DD.md.
- [x] Seed `memory/positions.md` — empty starting state, $100k cash.
- [x] Automate pre-market routine via Windows Task Scheduler (`scripts/run_pre_market.ps1`, runs daily at 7:30 AM ET weekdays).
- [ ] Run pre-market routine for 5 consecutive trading days. Verify output quality and that memory/daily/ is committed each day.
- [ ] Iterate on prompt and rules based on observed output.

**Exit criteria:** Pre-market routine produces useful, trustworthy output 5 days in a row.

### Phase 3 — Paper execution

- [ ] Wire up `skills/alpaca/` to actually place paper orders.
- [ ] Implement order gating through `guardrails/`.
- [ ] Add `routines/market_open.md` to execute approved trades.
- [ ] Add `routines/eod.md` to log results.
- [ ] Run manually for ~1 week, verify positions.md stays in sync with Alpaca.

**Exit criteria:** Bot can be invoked manually, places paper trades correctly, never violates guardrails (verified by tests).

### Phase 4 — Cron / scheduled autonomy

- [ ] Add `routines/midday.md` and `routines/weekly.md`.
- [ ] Set up local OS scheduler (Task Scheduler / cron) to run all five routines.
- [ ] Decide on cloud deploy (GitHub Actions vs Railway vs other) and migrate.
- [ ] Add error alerting (email on routine failure).

**Exit criteria:** Bot runs unattended for 2 weeks without intervention. Memory logs are coherent.

### Phase 5 — Fidelity signaling layer

- [ ] Add `skills/notifications/` for email (and optionally Slack).
- [ ] Modify `routines/market_open.md` to emit a "Fidelity action list" alongside paper execution.
- [ ] Format: "Buy 12 shares VTI at market" — copy-pasteable into Fidelity.
- [ ] Add a daily reconciliation: compare paper Alpaca positions vs. user's Fidelity holdings (manually entered into a `fidelity_state.md` file the user updates).

**Exit criteria:** User receives actionable trade emails and successfully executes them in Fidelity for 2+ weeks.

### Phase 6 — Refinement

- [ ] Backtest the strategy against historical data (Alpaca historical + yfinance).
- [ ] Compliance review: walk through `memory/decisions/` with employer compliance team if required.
- [ ] Tune guardrails based on observed behavior.
- [ ] Document any strategy revisions as ADRs.

**Exit criteria:** Strategy has measured edge over a buy-and-hold SPY benchmark across the paper period, OR strategy is revised with documented rationale.

### Phase 7 — Performance data capture (in progress — April 28, 2026)

This phase must ship before Phase 8 (the UI). The UI can only show data we have already collected, and every day this is delayed is a day of performance history lost. Backfilling from prose memory logs is unreliable.

**Why now**: The bot is running on Alpaca paper but `memory/timeseries/` does not exist. Daily memory logs are prose — they can be read but not charted. We need structured CSV capture starting with the next EOD run.

**What gets captured**: Three append-only CSVs in `memory/timeseries/`, written by the EOD routine after market close.

**`portfolio_daily.csv`** — one row per trading day:

| Column | Type | Source |
|---|---|---|
| date | YYYY-MM-DD | EOD timestamp |
| equity | float | Alpaca account.equity |
| cash | float | Alpaca account.cash |
| positions_value | float | Alpaca account.long_market_value |
| daily_pnl | float | today_equity - yesterday_equity |
| daily_pnl_pct | float | daily_pnl / yesterday_equity |
| cumulative_pnl | float | today_equity - starting_equity |
| cumulative_pnl_pct | float | cumulative_pnl / starting_equity |

**`positions_daily.csv`** — one row per (date, ticker) held:

| Column | Type | Source |
|---|---|---|
| date | YYYY-MM-DD | EOD timestamp |
| ticker | string | Alpaca position.symbol |
| quantity | float | Alpaca position.qty |
| avg_cost | float | Alpaca position.avg_entry_price |
| market_price | float | Alpaca position.current_price |
| market_value | float | Alpaca position.market_value |
| unrealized_pnl | float | Alpaca position.unrealized_pl |
| weight_pct | float | market_value / portfolio_equity |

**`benchmarks_daily.csv`** — one row per (date, benchmark):

| Column | Type | Source |
|---|---|---|
| date | YYYY-MM-DD | EOD timestamp |
| benchmark | string | "SPY", "AGG", "VT", "60_40_BLEND" |
| close_price | float | Alpaca historical bar (null for blends) |
| daily_return_pct | float | computed from prior day close |
| cumulative_return_pct | float | computed from start_date close |

**Initial benchmarks**: SPY (US equity baseline), AGG (US bond baseline), 60_40_BLEND (60% SPY + 40% AGG, computed — most honest comparison for a balanced strategy), VT (global equity).

**Why CSV**: trivial to write, trivial to read into pandas/Excel, auditable in git diffs, append-only by nature. Alternatives (JSON, sqlite, Parquet) add complexity without benefit at this scale.

**Implementation tasks**:
- [x] Create `memory/timeseries/` directory (created on first write by recorder; tracked via the CSVs themselves).
- [x] `skills/timeseries/recorder.py` — three idempotent append/update functions (re-running EOD same day must not duplicate rows). All `_pct` columns are decimal ratios (0.0123 = 1.23%).
- [x] `skills/timeseries/benchmarks.py` — fetch benchmark closes via Alpaca historical bars using `feed=DataFeed.IEX` (free-tier blocks recent SIP data). 60/40 blend computed in the recorder, daily-rebalanced from SPY+AGG dailies.
- [x] Update `routines/eod.md` to call the recorder after position reconciliation, before commit.
- [x] `scripts/backfill_benchmarks.py` — populate `benchmarks_daily.csv` from the bot's start date (2026-04-19) through yesterday. Portfolio CSV cannot be backfilled and starts fresh from Phase 7 ship date (2026-04-28).
- [x] `tests/test_timeseries.py` — idempotence, math correctness, schema validation, blend math (17 tests).
- [ ] `docs/decisions/NNNN-timeseries-format.md` ADR explaining CSV choice and schema rationale.

**Exit criteria**:
- EOD routine has written valid rows to all three CSVs for 5+ consecutive trading days. *(1/5 as of 2026-04-28; Phase 7 ship date.)*
- Re-running EOD on the same day does not create duplicate rows. *(Verified by tests + manual re-run on ship date.)*
- Benchmarks CSV has historical data going back to 2026-04-19. *(Backfilled 2026-04-20 → 2026-04-28; 2026-04-19 was a Sunday with no bar.)*
- All tests pass. *(35/35.)*

---

### Phase 8 — Performance UI

After Phase 7 has been collecting data for at least 2-3 weeks (enough to make charts meaningful), build a dashboard.

**Architectural options**:
- **Option A — Static HTML (recommended for v1)**: A script regenerates a single HTML file after each EOD run and commits it to the repo. Zero infrastructure, free, works without the dashboard ever being "running."
- **Option B — Local Streamlit app**: Interactive, but requires manual launch; PC must be on.
- **Option C — Hosted dashboard** (Streamlit Cloud, Render): Always-on, accessible from phone. Adds hosting cost and exposes positions outside the local machine — defer unless there's a clear reason.

Start with Option A. Upgrade to B if interactivity matters. Skip C unless data needs to leave the machine.

**Dashboard sections, in priority order**:
1. **Equity curve vs benchmarks** — bot's equity overlaid with SPY, AGG, 60/40. Single most important chart. Answers "is this strategy worth the complexity?"
2. **Daily P&L** — bar chart, 30/90 day windows.
3. **Current allocation** — pie/donut by ticker.
4. **Drawdown chart** — running drawdown from prior high water mark.
5. **Performance summary** — total return, annualized return, volatility, Sharpe, max drawdown, beta to SPY, alpha vs 60/40.
6. **Recent trades** — pulled from `memory/decisions/`, last 10 with rationale.
7. **Regime history** — color-coded calendar of identified regimes.

**Implementation tasks**:
- [ ] Decide A vs B based on how Phase 7 data feels after a few weeks.
- [ ] `dashboard/` directory with rendering logic (matplotlib + plotly for static; Streamlit + plotly for interactive).
- [ ] Hook into EOD for automatic regeneration (Option A) or document launch command (Option B).
- [ ] `dashboard/README.md` explaining how to view and what each chart means.

**Exit criteria**:
- Dashboard renders without errors on real data.
- Equity-curve-vs-60/40 makes "is the strategy beating passive 60/40?" answerable in under 2 seconds.
- Performance summary values match independent pandas calculation.

**Open question for later**: Once Fidelity manual execution starts, the real portfolio diverges from Alpaca paper. Does the dashboard track paper, real Fidelity holdings, or both side-by-side? Decide as part of Phase 5 (Fidelity reconciliation), not now.

---

## 7. Risks & mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| API keys leak via git commit | High | `.env` in `.gitignore` from commit 1. Use `git-secrets` or pre-commit hook. Repo is private. |
| Bot violates compliance rule | High | Hard-coded guardrails in front of every order. Restricted list checked on every trade. ETF-only whitelist enforced. |
| Bot blows up paper account | Low (it's paper) | Position size limits. Max trades per day. Stop-losses. Even paper failures are signals to fix the strategy. |
| Strategy underperforms benchmark | Medium | That's why we paper-trade for weeks before signaling Fidelity. If it doesn't beat SPY, it doesn't go live. |
| Cron job silently fails | Medium | Each routine writes to `memory/daily/`. EOD routine alerts if no entries since prior day. Add Healthchecks.io ping. |
| Alpaca API outage | Low | Routine should fail gracefully and alert, not retry forever. Resume on next scheduled run. |
| User executes wrong trade in Fidelity | Medium | Signal email includes ticker, side, quantity, and a unique signal ID. User confirms execution back to a `fidelity_state.md` file. |
| LLM hallucinates a trade not in strategy | Medium | Guardrails reject any ticker not on the whitelist. Reject any trade not justified by a rule the bot can cite. |
| Employer compliance later restricts something the bot was doing | Medium | All decisions are auditable in `memory/decisions/`. Restricted list is a single file to update. |

---

## 8. Open questions to resolve before Phase 1

1. **Compliance — Alpaca approval status?** (User is asking employer.)
2. **Compliance — ETF whitelist required, or open universe?** (User is asking.)
3. **Strategy — what's the initial ETF universe?** (Will draft in Phase 1; needs user review.)
4. **Strategy — what's the initial regime classification logic?** (Default proposal: yield curve slope + VIX percentile + 200-day SMA on SPY.)
5. **Notification channel — email, Slack, both?** (Defer to Phase 5.)
6. **Deploy target — local cron, GitHub Actions, Railway, other?** (Defer to Phase 4.)

---

## 9. References

- Nate Herk — *I Turned Claude Opus 4.7 Into a 24/7 Trader* — [https://www.youtube.com/watch?v=6MC1XqZSltw](https://www.youtube.com/watch?v=6MC1XqZSltw) — primary architectural inspiration.
- Samin Yasar — *Claude Just Changed the Stock Market Forever! (Tutorial)* — [https://www.youtube.com/watch?v=lH5wrfNwL3k](https://www.youtube.com/watch?v=lH5wrfNwL3k) — useful for Alpaca MCP setup, trailing stop concepts.
- Claude Code model configuration — [https://code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config)
- Alpaca paper trading — [https://docs.alpaca.markets/](https://docs.alpaca.markets/)

---

## 10. Definition of done (v1)

The project is "v1 done" when all of the following are true:

- Bot has been paper-trading autonomously on Alpaca for 30+ days with no manual intervention required.
- User has been receiving and executing Fidelity signals for 14+ days.
- Strategy performance vs SPY benchmark is documented in a weekly review.
- Compliance has signed off (or the user has confirmed no sign-off is required).
- Repo, decisions, and memory logs are complete and would let a third party reconstruct every trade.
- Phase 7 data capture has run for 30+ trading days with no missing rows.
- Dashboard renders correctly; equity curve vs 60/40 benchmark documented in a weekly review with discussion of whether the bot is earning its complexity.

After v1, candidate v2 features include: backtesting framework, strategy variations, multi-account support, tax-aware rebalancing, options (if compliance ever allows).
