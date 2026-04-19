# Autonomous ETF Trading Bot — Project Plan

> **Status:** Draft v1 — Sunday, April 19, 2026
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

### Phase 0 — Environment setup (target: 1 session)

- [ ] Install / update Claude Code CLI (`claude update`, confirm v2.1.111+ for Opus 4.7).
- [ ] Create private GitHub repo `autonomous-etf-trader`.
- [ ] Clone locally, open in VS Code.
- [ ] Create Alpaca paper trading account, generate API keys.
- [ ] Create `.env` from `.env.example`, populate Alpaca paper keys.
- [ ] Decide language (Python vs TypeScript) — Claude Code recommends, user approves.
- [ ] Initial commit: `PLAN.md`, `README.md`, `.gitignore`, `.env.example`, language scaffolding.
- [ ] Verify Alpaca connection with a one-line "get account" call.

**Exit criteria:** Repo exists on GitHub, Alpaca paper account responds to API call, `claude` runs in the project directory.

### Phase 1 — Strategy & guardrails (no execution)

- [ ] Draft `strategy/universe.md` — initial ETF whitelist (~15-25 tickers across asset classes).
- [ ] Draft `strategy/rules.md` — regime-based tactical asset allocation in plain English.
- [ ] Draft `strategy/regimes.md` — risk-on/risk-off signals (yield curve, VIX, momentum).
- [ ] Draft `guardrails/hard_limits.md` and matching code in `skills/guardrails/`.
- [ ] Write `guardrails/restricted.md` (start empty; populate as compliance answers come in).
- [ ] Write `CLAUDE.md` — instructions for Claude Code on how to work in this repo.

**Exit criteria:** A human can read the strategy and guardrails and understand exactly what the bot will and won't do.

### Phase 2 — Single routine, manual trigger

- [ ] Implement `routines/pre_market.md` (the prompt) + supporting `skills/`.
- [ ] Run it manually via `claude`. Verify it produces a sensible market briefing and trade proposals.
- [ ] No order execution yet — output to console only.
- [ ] Iterate on prompt and rules until output quality is good.

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

After v1, candidate v2 features include: backtesting framework, strategy variations, multi-account support, tax-aware rebalancing, options (if compliance ever allows).
