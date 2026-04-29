# Autonomous ETF Trading Bot — Project Plan

> **Status:** Phases 0–3 + 7 complete; Phase 4 closing — Tuesday, April 28, 2026
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

The architecture is designed to work in the most restrictive plausible case so we are not blocked while waiting for answers.

| # | Question | Status |
|---|---|---|
| 1 | Is **Alpaca** an approved broker for personal accounts (even paper trading)? | **Pending** — assume yes for paper; confirm before real-money use |
| 2 | Does the ETF restriction require a **defined whitelist** or is any ETF allowed? | **Resolved 2026-04-24** — Yes. Firm Appendix 2 is the approved list. Encoded in `strategy/appendix_2_approved.json` and enforced by `skills/guardrails/checker.py`. |
| 3 | Are there **holding-period requirements** (e.g., 30/60-day minimum)? | **Pending** — assume 30 days. Strategy avoids frequent rotation per Rule 3.4. |
| 4 | Is there a **restricted ETF list** (sector ETFs touching employer industry, etc.)? | **Resolved 2026-04-24** — Firm Appendix 3 lists removed tickers; encoded in `guardrails/restricted.md`. |
| 5 | Are **duplicate confirms / 407 letters** required? | **Pending** — relevant for Fidelity setup; no impact on Alpaca paper |
| 6 | Do **blackout windows** apply to ETF trades? | **Pending** — `guardrails/blackouts.md` has no employer blackouts yet |

Detailed answers and impact notes live in `docs/compliance.md`.

---

## 4. Tooling decisions

| Decision | Choice | Rationale |
|---|---|---|
| Editor | **VS Code** | User already has it; integrated terminal hosts Claude Code. |
| AI agent | **Claude Code CLI** (not Claude Desktop) | Built for agentic, autonomous, multi-step file/terminal/git work. Same tool the bot will use in production. |
| Model strategy | **`/model opusplan`** | Built-in hybrid: Opus 4.7 for planning, Sonnet 4.6 for execution. No manual switching needed. Manually `/model opus` for deep architecture sessions, `/model sonnet` for pure implementation. |
| Language | **Python** | Best Alpaca SDK (`alpaca-py`), richest finance ecosystem. Full reasoning in `docs/decisions/0001-language.md` (TODO). |
| Version control | **Git + private GitHub repo** | Required for auditability, secrets isolation, deploy targets later. |
| Secrets | **`.env` file (gitignored) + `1Password` or OS keychain for backup** | Never commit API keys. Document the required env vars in `.env.example`. |
| Scheduling (current) | **Windows Task Scheduler** | Free, simple, sufficient for paper trading. PC must stay on. |
| Scheduling (later) | **Cloud cron** (GitHub Actions, Railway, or similar) | Decide if/when local scheduling becomes a real constraint. Cost is the main blocker; user has noted ~$1–3/day GitHub Actions estimate is too high. |
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
| **Market open** | Weekdays 9:35 AM ET | Reviews drafted trades against current prices. Executes on Alpaca paper. (Pure-Python execution; no LLM prompt — drafts come from pre-market `memory/proposals/` JSON.) |
| **Midday scan** | Weekdays 12:30 PM ET | Checks open positions vs. stops and targets. Flags trailing-stop breaches for next-day exit. |
| **End-of-day summary** | Weekdays 4:15 PM ET | Logs P&L, position changes, writes daily entry to memory log + timeseries CSVs. |
| **Weekly review** | Fridays 5:00 PM ET | Computes weekly performance, regime accuracy, signal hit rate. Proposes strategy tweaks for human review (does not auto-apply). |

### Repo structure

```
.
├── README.md                   # Project overview, quick-start
├── PLAN.md                     # This document
├── CLAUDE.md                   # Instructions for Claude Code itself
├── .env.example                # Template for required secrets
├── .gitignore                  # Excludes .env, memory/private/, etc.
├── requirements.txt
│
├── strategy/
│   ├── universe.md             # Approved ETF list (curated shortlist) — references the JSON below
│   ├── appendix_2_approved.json # Authoritative firm-approved whitelist (~230 tickers)
│   ├── rules.md                # Entry/exit/sizing rules in plain English
│   ├── regimes.md              # Risk-on / risk-off classification logic
│   └── thesis.md               # Why this strategy is expected to work
│
├── guardrails/
│   ├── hard_limits.md          # Max position size, max trades/day, etc.
│   ├── restricted.md           # Appendix 3 removals + bot-imposed restrictions
│   └── blackouts.md            # Date ranges where no trading occurs
│
├── routines/
│   ├── pre_market.md           # 7-step LLM prompt for pre-market briefing + proposals
│   ├── midday.md               # 5-step LLM prompt for intraday checks
│   ├── eod.md                  # 6-step LLM prompt for end-of-day summary + timeseries
│   └── weekly.md               # 7-step LLM prompt for Friday review (read-only proposals)
│   # Note: market-open is pure Python (scripts/market_open.py) — no LLM prompt needed,
│   # since proposals are pre-staged by pre-market in memory/proposals/YYYY-MM-DD.json.
│
├── skills/
│   ├── alpaca/                 # Wrapper functions for Alpaca paper API
│   ├── market_data/            # yfinance / FRED / Alpaca data wrapper
│   ├── timeseries/             # CSV recorder + benchmark fetcher
│   ├── notifications/          # Email / Slack senders (Phase 5)
│   ├── guardrails/             # Order-gate enforcement code
│   └── memory/                 # Read/write to memory logs
│
├── memory/
│   ├── decisions/              # One markdown file per trade decision
│   ├── daily/                  # YYYY-MM-DD.md daily logs
│   ├── weekly/                 # YYYY-Www.md weekly review files
│   ├── proposals/              # Pre-market trade proposals queued for market-open
│   ├── timeseries/             # portfolio_daily.csv, positions_daily.csv, benchmarks_daily.csv
│   ├── highwatermarks.json     # Per-ticker peak tracking for trailing stops
│   └── positions.md            # Current paper position state
│
├── scripts/
│   ├── setup_scheduler.ps1     # One-time: register all 5 Task Scheduler tasks
│   ├── run_pre_market.ps1      # Wrapper: pre-market routine
│   ├── run_market_open.ps1     # Wrapper: market-open execution
│   ├── run_midday.ps1          # Wrapper: midday routine
│   ├── run_eod.ps1             # Wrapper: EOD routine
│   ├── run_weekly.ps1          # Wrapper: weekly review
│   ├── market_open.py          # Pure-Python order placer (no LLM)
│   ├── midday.py               # Position data helper invoked by midday routine
│   ├── eod.py                  # Position + timeseries helper invoked by EOD routine
│   ├── hello_alpaca.py         # Phase 0 smoke test
│   ├── test_order.py           # Manual order test utility
│   └── backfill_benchmarks.py  # Phase 7 historical benchmark loader
│
├── logs/                       # Per-routine, per-day .log files (gitignored)
│
├── docs/
│   ├── compliance.md           # Open questions, answers as they arrive
│   ├── compliance_source/      # Source firm-policy PDFs
│   ├── decisions/              # ADRs (architecture decision records)
│   └── runbook.md              # How to operate / debug the bot
│
└── tests/
    ├── test_guardrails.py      # Verify guardrails actually block bad trades
    └── test_timeseries.py      # Phase 7 idempotence + math correctness
```

### Why markdown for strategy and memory

This is the key insight from Nate Herk's video: **the bot reads and writes its own memory and rules in markdown, not in a database**. The agent is a language model — markdown is its native format. Strategy rules in plain English are easier to write, easier to audit, and easier for the bot to follow correctly than JSON config or code. The bot reasons about the rules; it doesn't just execute them.

### Hard guardrails are code, not prompts

Soft guidance ("prefer broad-market ETFs") goes in markdown the bot reads. **Hard limits ("never trade more than 30% of portfolio in a single position") are enforced in code that gates every order before it reaches Alpaca.** A prompt can be ignored or misread; a Python `if` statement cannot. The guardrails layer is the safety net.

### Why market-open has no LLM prompt

Pre-market produces a structured proposal file (`memory/proposals/YYYY-MM-DD.json`) listing every order with ticker, side, notional, and rule citations. By 9:35 AM ET, the work of *deciding* what to trade is done. The market-open script just iterates the proposals, runs each through the guardrails checker, and submits to Alpaca. No reasoning is needed, so there's no LLM call — keeping market-open fast (5–10 seconds), deterministic, and cheap. If the LLM is ever needed at open (e.g., a regime change overnight invalidates the proposals), pre-market should regenerate proposals — not market-open.

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

**Exit criteria:** Met.

### Phase 1 — Strategy & guardrails (no execution) ✅ complete (April 19, 2026)

- [x] Draft `strategy/universe.md` — initial 15 ETFs; expanded 2026-04-24 to reference firm Appendix 2 (`appendix_2_approved.json`, ~230 approved tickers).
- [x] Draft `strategy/rules.md` — 8 rule groups. *VIG → DGRO substitution made 2026-04-28 to align with Appendix 2.*
- [x] Draft `strategy/regimes.md` — three-signal classifier: SPY vs 200-day SMA, VIX level, 10yr-2yr yield curve spread. Majority vote, 2-day confirmation.
- [x] Draft `strategy/thesis.md` — why regime persistence justifies tactical allocation; falsification criteria defined.
- [x] Draft `guardrails/hard_limits.md` — 10-step sequential gate model.
- [x] Write `guardrails/restricted.md` — populated 2026-04-24 with Appendix 3 removals + bot-imposed restrictions (VIXY, VXX, SH).
- [x] Write `guardrails/blackouts.md` — NYSE holidays via Alpaca API; employer blackouts empty pending compliance.
- [x] Write `docs/compliance.md` — 6 open questions; #2 and #4 resolved 2026-04-24.
- [ ] Write `docs/decisions/0001-language.md` — ADR documenting Python choice. *(TODO — see Phase 9.)*
- [x] Write `CLAUDE.md` — committed in Phase 0.

**Exit criteria:** Met.

### Phase 2 — Single routine, automated via local Task Scheduler ✅ complete (April 28, 2026)

- [x] Implement `routines/pre_market.md` — full 7-step prompt: fetch signals, check prior regime, read strategy, draft proposals, market context, log to memory, print summary.
- [x] Implement `skills/market_data/fetcher.py` — pulls SPY 200d SMA (yfinance), VIX (yfinance), 10yr-2yr spread (FRED). Majority-vote regime classifier.
- [x] Implement `skills/guardrails/checker.py` — 10-step sequential order gate. CLI-invokable. Reads universe/restricted/blackouts at runtime. Updated 2026-04-24 to enforce against `appendix_2_approved.json`.
- [x] Implement `skills/memory/logger.py` — appends timestamped entries to memory/daily/YYYY-MM-DD.md.
- [x] Seed `memory/positions.md` — empty starting state, $100k cash.
- [x] Automate pre-market routine via Windows Task Scheduler (`scripts/run_pre_market.ps1`, runs daily at 7:30 AM ET weekdays).
- [x] Pre-market routine ran cleanly for 7 consecutive trading days (2026-04-20 through 2026-04-28).

**Exit criteria:** Met.

### Phase 3 — Paper execution ✅ complete (April 28, 2026)

- [x] Wire up `skills/alpaca/` to place paper orders.
- [x] Implement order gating through `guardrails/` (every order goes through `skills/guardrails/checker.py` first).
- [x] Add `scripts/market_open.py` — pure-Python order placer (consumes pre-market proposal JSON; no LLM prompt needed since decisions are pre-staged).
- [x] Add `routines/eod.md` to log results, update positions.md, write timeseries CSVs.
- [x] Add `routines/midday.md` for trailing stop checks.
- [x] First live paper trades placed 2026-04-27 market open: 4 buys (VTI, QQQ, BND, VEA).
- [x] 2026-04-28 market open: 5 additional buys (VTI/QQQ top-ups, DGRO/VWO/HYG opens), hitting daily 5-trade cap exactly.
- [x] `memory/positions.md` reconciles cleanly with Alpaca after each routine.

**Exit criteria:** Met. Bot places paper trades correctly. Decision logs cite specific rule numbers. No guardrail violations observed.

### Phase 4 — Cron / scheduled autonomy 🟡 closing — observation window (target close: 2026-05-08)

This phase requires *both* working scheduling code AND a clean unattended-run track record. The code is done; the wait is for the calendar.

**Code & configuration ✅ complete**
- [x] `scripts/setup_scheduler.ps1` registers all five tasks (`AutoTrading-PreMarket/MarketOpen/Midday/EOD/Weekly`).
- [x] All five wrapper scripts exist: `run_pre_market.ps1`, `run_market_open.ps1`, `run_midday.ps1`, `run_eod.ps1`, `run_weekly.ps1`.
- [x] Pre-market firing on schedule for 7 consecutive trading days (2026-04-20 → 04-28).
- [x] Market-open, midday, EOD all firing on schedule for 2 consecutive trading days (2026-04-27, 04-28). *Earlier days had logs at off-hours, indicating manual catch-up runs before the schedule was registered.*
- [x] `routines/weekly.md` — Friday review routine (created 2026-04-28). First scheduled run: Fri 2026-05-01 at 5:00 PM ET. Note: requires `setup_scheduler.ps1` to be re-run as Administrator to register the new `AutoTrading-Weekly` task.
- [x] Cloud deploy decision **deferred** — Windows Task Scheduler is sufficient. GitHub Actions cost (~$1–3/day) is too high without a clear win. User has explicitly accepted the "PC must stay on" constraint.

**Observation window ⏳ in progress**
- [ ] 14 consecutive trading days of clean unattended runs across all 4 daily routines, plus one full weekly review. *Day 2 of 14 as of 2026-04-28. Target close: Thu 2026-05-08 (assuming no missed days).*
- [ ] Weekly routine fires Fri 2026-05-01 and produces a valid `memory/weekly/2026-W18.md` review.

**Deferred to Phase 5**
- ~~Add error alerting (email on routine failure)~~ — moved to Phase 5 since email is the primary deliverable there. Logs are local-only until then.

**Exit criteria:** Bot runs unattended for 14 trading days without manual intervention. All five routines (pre-market, market-open, midday, EOD, weekly) fire on schedule. Memory logs and timeseries CSVs are coherent and complete. *Target: 2026-05-08.*

### Phase 5 — Fidelity signaling layer

> **User intent (2026-04-28):** Hold off ~1 month before starting Phase 5 to gather paper performance data first. Earliest start ~2026-05-28.

- [ ] Add `skills/notifications/` for email (and optionally Slack/WhatsApp/Telegram).
- [ ] Modify `scripts/market_open.py` (or add a post-step) to emit a "Fidelity action list" alongside paper execution.
- [ ] Format: "Buy 12 shares VTI at market" — copy-pasteable into Fidelity.
- [ ] Add a daily reconciliation: compare paper Alpaca positions vs. user's Fidelity holdings (manually entered into a `fidelity_state.md` file the user updates).
- [ ] Add error alerting: any routine wrapper that exits non-zero sends an email so missed runs are not silent.

**Exit criteria:** User receives actionable trade emails and successfully executes them in Fidelity for 2+ weeks.

### Phase 6 — Refinement

- [ ] Backtest the strategy against historical data (Alpaca historical + yfinance).
- [ ] Compliance review: walk through `memory/decisions/` with employer compliance team if required.
- [ ] Tune guardrails based on observed behavior.
- [ ] Document any strategy revisions as ADRs.

**Exit criteria:** Strategy has measured edge over a buy-and-hold SPY benchmark across the paper period, OR strategy is revised with documented rationale.

### Phase 7 — Performance data capture ✅ complete (April 28, 2026)

This phase shipped before Phase 8 (the UI). The UI can only show data we have already collected.

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

**Implementation**:
- [x] Create `memory/timeseries/` directory.
- [x] `skills/timeseries/recorder.py` — three idempotent append/update functions. All `_pct` columns are decimal ratios (0.0123 = 1.23%).
- [x] `skills/timeseries/benchmarks.py` — fetch benchmark closes via Alpaca historical bars using `feed=DataFeed.IEX` (free-tier blocks recent SIP data). 60/40 blend computed in the recorder, daily-rebalanced from SPY+AGG dailies.
- [x] Update `routines/eod.md` to call the recorder after position reconciliation, before commit.
- [x] `scripts/backfill_benchmarks.py` — populate `benchmarks_daily.csv` from 2026-04-19 through yesterday. Portfolio CSV starts fresh from Phase 7 ship date (2026-04-28).
- [x] `tests/test_timeseries.py` — idempotence, math correctness, schema validation, blend math (17 tests).
- [ ] `docs/decisions/NNNN-timeseries-format.md` ADR. *(TODO — see Phase 9.)*

**Exit criteria:** Met (apart from the ADR).
- ✅ EOD wrote valid rows on first live run (2026-04-28).
- ✅ Re-running EOD same day does not duplicate rows (verified by tests + manual re-run).
- ✅ Benchmarks CSV backfilled 2026-04-20 → 2026-04-28.
- ✅ All 35 tests pass.

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

### Phase 9 — Documentation backfill

Small phase to clean up outstanding docs the project should have. Not blocking anything but the architectural decisions deserve preservation.

- [ ] `docs/decisions/0001-language.md` — Why Python over TypeScript (Alpaca SDK quality, finance ecosystem, scheduling tooling).
- [ ] `docs/decisions/0002-markdown-first.md` — Why markdown for strategy/rules/memory rather than JSON or a database.
- [ ] `docs/decisions/0003-csv-timeseries.md` — Why CSV for `memory/timeseries/` over JSON/sqlite/Parquet (Phase 7 design).
- [ ] `docs/decisions/0004-appendix2-whitelist.md` — Why a JSON-as-source-of-truth + markdown shortlist split (Compliance §2 resolution).
- [ ] `docs/decisions/0005-half-step-rebalance.md` — Why Rule 4.2 says "rebalance at most 50% of the gap per session."
- [ ] `docs/decisions/0006-no-llm-at-market-open.md` — Why market-open is pure Python instead of an LLM-driven routine.

**Exit criteria:** All six ADRs exist and follow the Context → Decision → Consequences format.

---

### Phase 10 — Strategy diversification (deferred until ~June 2026)

> Placeholder. Do not implement until Phase 4 has closed AND at least 30 trading days of clean performance data exist for the primary regime strategy. The right second strategy depends on the failure mode of the first one — pick the strategy that addresses the specific weakness observed, not the one that sounds best in the abstract.

**Rationale for adding a second strategy at all:** Two uncorrelated strategies each returning 5% are better than one returning 7% — combined volatility drops, drawdowns shrink. But each new strategy adds operational complexity, monitoring burden, and capital fragmentation. Add at most one parallel strategy, and only after the primary has demonstrated either edge or a clear weakness to address.

**Candidate strategies** (in priority order, all ETF-only and Appendix 2-compatible):

1. **Dual momentum (Antonacci variant)** — Two-step screen: own SPY only if its 12-month return beats T-bills (absolute momentum); between US and international equity, own whichever has stronger 12-month return (relative momentum); else hold AGG. Three positions ever held. Simplest to implement (~60 lines + rules markdown). Lowest operational complexity. Low turnover (monthly rebalance). Strong historical record though may have weakened post-publication.

2. **Sector / asset-class momentum rotation** — Rank a 9-ETF universe (SPY, QQQ, IWM, EFA, VWO, AGG, TLT, GLD, GSG) by 6 or 12-month total return; hold top 2-3, rotate when rankings change. Adds a momentum signal type that complements the regime classifier's macro signals. Higher turnover — may bind against the assumed 30-day holding period.

3. **Risk parity (All Weather variant)** — Static allocation balancing risk contribution rather than capital across stocks/bonds/gold (~30/50/20 typical). Rebalance quarterly. Could be implemented as a third "REGIME = UNCERTAIN" allocation in the existing rules rather than a parallel system. Tickers already in the curated shortlist.

**Strategies considered and rejected:**
- Politician trade copying (NANC/KRUZ et al.): Politicians trade individual stocks and options — both prohibited. Tracker ETFs not on Appendix 2. Compliance optics. See conversation 2026-04-28.
- Pairs trading / mean reversion: Requires shorting (prohibited).
- Trend-following on broad assets: Mechanically similar to existing regime classifier — limited diversification benefit.
- Macro thematic (AI, clean energy, etc.): Concentrated single-bet wrapped as a "strategy" — effectively just stock-picking with extra steps.
- Buy-write / covered call income: Compliance prohibits selling options. Wrapped versions (JEPI, JEPQ, GPIX) are on Appendix 2 but better treated as positions in an income tilt, not a parallel strategy.
- Smart-beta factor strategies (value, quality, low-vol): Better expressed as tilts within the existing regime allocation, not parallel systems.

**Volatility targeting** is worth considering but is an *overlay* (rule modification) on the existing strategy, not a parallel strategy. Same for adding factor tilts — these are rule changes, not new architectures.

**Decision framework before adding:**
- Run primary strategy through May 2026 with no changes
- In each weekly review, characterize the failure mode: was the bot too slow, did it whipsaw, did it lag in trends, did the 60/40 blend beat it consistently?
- Pick the candidate that addresses the observed failure mode
- Allocate at most 30% of portfolio to the second strategy initially
- Run with separate `strategy/<name>/` folder, separate `memory/timeseries/` columns, separate decision logs

**Implementation plan when triggered:**
- [ ] ADR documenting which strategy chosen and why (`docs/decisions/00NN-second-strategy.md`)
- [ ] New `strategy/<name>/` directory mirroring the structure of the primary
- [ ] Decide capital split. Default: 70% primary / 30% secondary
- [ ] Extend `memory/positions.md` and timeseries CSVs with strategy attribution
- [ ] Extend the weekly review to compare strategies head-to-head
- [ ] Update guardrails to enforce per-strategy limits (no single position > 30% of *total* equity, regardless of which strategy)

**Exit criteria:** Second strategy runs in parallel for 30+ trading days. Weekly reviews compare both. Performance attribution is unambiguous.

---

## 7. Risks & mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| API keys leak via git commit | High | `.env` in `.gitignore` from commit 1. Use `git-secrets` or pre-commit hook. Repo is private. |
| Bot violates compliance rule | High | Hard-coded guardrails in front of every order. Restricted list checked on every trade. ETF-only whitelist enforced. |
| Bot blows up paper account | Low (it's paper) | Position size limits. Max trades per day. Stop-losses. Even paper failures are signals to fix the strategy. |
| Strategy underperforms benchmark | Medium | That's why we paper-trade for weeks before signaling Fidelity. If it doesn't beat SPY, it doesn't go live. |
| Cron job silently fails | Medium | Each routine writes to `memory/daily/`. EOD routine alerts if no entries since prior day. Email alerting deferred to Phase 5. |
| Alpaca API outage | Low | Routine should fail gracefully and alert, not retry forever. Resume on next scheduled run. |
| User executes wrong trade in Fidelity | Medium | Signal email includes ticker, side, quantity, and a unique signal ID. User confirms execution back to a `fidelity_state.md` file. |
| LLM hallucinates a trade not in strategy | Medium | Guardrails reject any ticker not on the whitelist. Reject any trade not justified by a rule the bot can cite. |
| Employer compliance later restricts something the bot was doing | Medium | All decisions are auditable in `memory/decisions/`. Restricted list is a single file to update. |
| Local PC outage misses scheduled runs | Medium | Bot runs only when PC is on. User has accepted this constraint; cloud cron deferred for cost reasons. EOD routine should detect missed prior-day runs. |
| New `AutoTrading-Weekly` task not registered | Low (one-time) | `setup_scheduler.ps1` updated 2026-04-28 to include the weekly task. Must be re-run as Administrator before Friday 2026-05-01 or the first weekly review will not fire. |

---

## 8. Open questions to resolve before Phase 1

*(Historical — Phase 1 is complete. Retained for context.)*

1. **Compliance — Alpaca approval status?** *(Pending — assumed yes for paper.)*
2. **Compliance — ETF whitelist required, or open universe?** *(Resolved: yes, Appendix 2.)*
3. **Strategy — what's the initial ETF universe?** *(Resolved: 15-ticker shortlist + ~230 Appendix 2 whitelist.)*
4. **Strategy — what's the initial regime classification logic?** *(Resolved: SPY 200d SMA + VIX + yield curve spread, majority vote, 2-day confirmation.)*
5. **Notification channel — email, Slack, both?** *(Defer to Phase 5.)*
6. **Deploy target — local cron, GitHub Actions, Railway, other?** *(Resolved for now: Windows Task Scheduler. Cloud deferred for cost.)*

---

## 9. References

- Nate Herk — *I Turned Claude Opus 4.7 Into a 24/7 Trader* — [https://www.youtube.com/watch?v=6MC1XqZSltw](https://www.youtube.com/watch?v=6MC1XqZSltw) — primary architectural inspiration.
- Samin Yasar — *Claude Just Changed the Stock Market Forever! (Tutorial)* — [https://www.youtube.com/watch?v=lH5wrfNwL3k](https://www.youtube.com/watch?v=lH5wrfNwL3k) — useful for Alpaca MCP setup, trailing stop concepts.
- Claude Code model configuration — [https://code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config)
- Alpaca paper trading — [https://docs.alpaca.markets/](https://docs.alpaca.markets/)

---

## 10. Definition of done (v1)

The project is "v1 done" when all of the following are true:

- Bot has been paper-trading autonomously on Alpaca for 30+ days with no manual intervention required. *(Started 2026-04-27.)*
- User has been receiving and executing Fidelity signals for 14+ days. *(Phase 5 not started; user holding ~1 month for paper data first.)*
- Strategy performance vs SPY benchmark is documented in a weekly review.
- Compliance has signed off (or the user has confirmed no sign-off is required).
- Repo, decisions, and memory logs are complete and would let a third party reconstruct every trade.
- Phase 7 data capture has run for 30+ trading days with no missing rows.
- Dashboard renders correctly; equity curve vs 60/40 benchmark documented in a weekly review with discussion of whether the bot is earning its complexity.
- All Phase 9 ADRs written.

After v1, candidate v2 features include: backtesting framework, strategy variations, multi-account support, tax-aware rebalancing, options (if compliance ever allows).

**Post-v1 candidates:** Phase 10 (strategy diversification) is explicitly deferred until after v1 — see Phase 10 for candidate strategies and decision framework.
