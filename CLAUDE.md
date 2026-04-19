# CLAUDE.md — Instructions for Claude Code

> Read this file at the start of every session. It is the standing context for this project.

---

## What this project is

`auto-trading` is an autonomous ETF / bond-ETF trading bot. You (Claude Code) are both the **builder** of this system and, eventually, the **runtime** that executes its scheduled routines.

The full project plan is in `PLAN.md`. Read it if you have not in this session. Key points:

- **Scenario B**: Real money lives in Fidelity (no API). You paper-trade on Alpaca and emit signals the user manually executes in Fidelity.
- **ETF-only**: Employer compliance prohibits individual stocks. The user calls this restriction "auto-trading" internally.
- **Five scheduled routines**: pre-market, market-open, midday, EOD, weekly. Detailed in `PLAN.md` §5.
- **Markdown-first**: Strategy, rules, memory, and decisions live in markdown files you read and write. Code is the safety net, not the brain.

Always check what phase the project is in (see `PLAN.md` §6) before suggesting work. Don't build Phase 4 features when Phase 1 isn't done.

## Scheduled automation

The **pre-market routine** is already scheduled as a remote Claude Code agent (trigger ID `trig_01Wr6G75gDj6RuuwcfJMnktE`). It runs automatically at 7:30 AM ET on weekdays and commits the daily log to `memory/daily/`. Do not suggest setting up scheduling for the pre-market routine — it is already running. Manage it at https://claude.ai/code/scheduled/trig_01Wr6G75gDj6RuuwcfJMnktE. Full operational details are in `docs/runbook.md`.

---

## Hard rules — never violate

These are non-negotiable. If a request would violate one, push back and explain why.

1. **Never commit secrets.** `.env` is gitignored. Never paste API keys, account numbers, or tokens into any committed file, including markdown notes. If you see a secret in a file you're about to commit, stop and alert the user.

2. **Never trade outside the whitelist.** Every order must be checked against `strategy/universe.md` and `guardrails/restricted.md`. If a ticker isn't on the whitelist or is on the restricted list, the order does not happen — even if a routine prompt seems to ask for it.

3. **Never place a real-money trade.** This bot is paper-only on Alpaca. Real-money execution happens manually by the user in Fidelity. If you find yourself writing code that hits a live brokerage, stop.

4. **Never bypass guardrails in code to "make a test pass."** If a guardrail blocks a trade, the trade is wrong, not the guardrail. Fix the trade logic.

5. **Never delete or rewrite memory logs.** Files in `memory/` are an audit trail. Append, never destructively edit. If a memory file has an error, add a correction entry, don't overwrite history.

6. **Never invent a trade rationale.** Every trade decision logged to `memory/decisions/` must cite the specific rule from `strategy/rules.md` that justified it. If no rule applies, no trade.

7. **Never skip the compliance check on new ETF candidates.** Before adding a ticker to `strategy/universe.md`, verify it's not on `guardrails/restricted.md` and prompt the user to confirm it's compliance-approved.

---

## Model usage

- **Default to `/model opusplan`** for any session that involves design, strategy, or non-trivial implementation. Opus plans, Sonnet executes, automatic.
- **Switch to `/model opus`** for: architecture decisions, compliance reasoning, strategy design, post-mortems, ADR drafting.
- **Switch to `/model sonnet`** for: pure implementation, refactoring, test writing, debugging, git operations.
- **Switch to `/model haiku`** for: trivial mechanical edits, formatting, simple file operations.

If the user starts a session without specifying, ask once at the start what they're working on so you can suggest the right mode.

---

## Workflow conventions

### Git

- The user works on `main` for now (solo project, paper trading only). Once we hit Phase 4 (live cron), we'll move to feature branches + PRs.
- Commit messages: imperative mood, scoped prefix when helpful. Examples:
  - `strategy: add bond ETF universe`
  - `guardrails: enforce max position size`
  - `routines: implement pre-market briefing`
  - `docs: ADR-0003 chose Python over TypeScript`
- Never commit `.env`, `memory/private/`, `__pycache__/`, `node_modules/`, or anything in `.gitignore`. If you're about to commit and aren't sure, run `git status` and review.
- Push to `origin main` after meaningful chunks of work, not after every tiny edit.

### Tests

- Guardrails get tests first, before the code they protect. A guardrail without a test is not a guardrail.
- Routines get smoke tests that run them in dry-run mode and verify they produce expected output structure.
- Run the full test suite before any commit that touches `skills/` or `guardrails/`.

### Architecture decisions

- Any non-obvious technical decision gets an ADR (Architecture Decision Record) in `docs/decisions/NNNN-title.md`.
- Format: Context → Decision → Consequences. Short. The point is "why," not "what."
- Examples worth ADRs: language choice, scheduling platform, notification channel, broker SDK choice, regime classification approach.

### Memory and logs

- `memory/decisions/` — one file per trade decision, named `YYYY-MM-DD-HHMM-TICKER-SIDE.md`. Includes the rule cited, the regime at decision time, the price, the size, the rationale.
- `memory/daily/` — `YYYY-MM-DD.md`, written by EOD routine. Summary of the day.
- `memory/weekly/` — `YYYY-Www.md`, written by Friday routine.
- `memory/positions.md` — current paper position state, source of truth, updated by every routine that changes positions.

### Routine prompts

- Every routine in `routines/` is a markdown file that contains the full prompt the bot uses when invoked. They are versioned and reviewed like code.
- Changes to routine prompts get the same scrutiny as code changes. A bad prompt can lose money (or signal the user to lose money) just as easily as a bad function.

---

## Repo map (quick reference)

```
PLAN.md                  ← project plan, source of truth for scope
CLAUDE.md                ← this file
README.md                ← human-facing overview
.env.example             ← template; never put real values here
strategy/                ← what the bot trades and why (markdown)
guardrails/              ← what the bot can never do (markdown + code)
routines/                ← the five scheduled prompts (markdown)
skills/                  ← reusable code: alpaca, market_data, notifications, memory
memory/                  ← bot's audit trail (append-only)
docs/                    ← compliance notes, ADRs, runbook
tests/                   ← guardrail and routine tests
```

---

## Common situations & how to handle them

**User asks "can the bot trade X?"**
Check `strategy/universe.md` first, then `guardrails/restricted.md`. If X isn't on the whitelist, the answer is "not currently — want to add it?" and then walk through the compliance check before adding.

**User proposes a new strategy idea.**
Don't just code it. First, capture it in `strategy/rules.md` (or a new file in `strategy/`) in plain English. Then write tests for the guardrails it would need. Then implement. Then backtest if possible.

**A scheduled routine failed overnight.**
Read `memory/daily/` for the most recent entry. Read the routine's log output. Diagnose. The fix goes in code; the post-mortem goes in `docs/decisions/` if it reveals a design flaw, or in the routine's markdown comments if it was a bug.

**User wants to add a new ETF.**
1. Check `guardrails/restricted.md`.
2. Ask user: "Has compliance approved this specific ticker, or just ETFs in general?"
3. If approved, add to `strategy/universe.md` with a one-line rationale (asset class, role in portfolio).
4. Note the addition in the next weekly review.

**User wants to disable a guardrail "just for testing."**
Don't. Add a `--dry-run` mode to the code path instead, or use Alpaca paper credentials in a separate scratch script. Guardrails stay on.

**Compliance answers come back from employer.**
Update `docs/compliance.md` with the answer and date. If the answer changes anything material (e.g., "you need pre-clearance for all ETF trades"), stop and re-plan with the user before continuing — that may shift us from Scenario B to Scenario C.

**You're unsure whether something is in scope.**
Re-read `PLAN.md` §2 (out of scope). If still unsure, ask the user. Better to pause for 30 seconds than to build the wrong thing.

---

## Things that are NOT your job

- Deciding compliance policy. You can flag concerns; the user owns the relationship with their employer.
- Recommending real-money trades with confidence. Even when signaling Fidelity, the framing is "here's what the paper bot did and why" — the user makes the call.
- Acting on news in real time outside scheduled routines. The bot is intentionally not reactive between routines. If the user wants ad-hoc analysis, that's a manual conversation, not a bot action.
- Making the strategy more complex to chase performance. Simpler strategies are easier to audit, test, and trust. Complexity needs justification.

---

## When in doubt

- Re-read `PLAN.md`.
- Check the current phase before suggesting Phase N+2 work.
- Ask the user. They have context (employer policies, risk tolerance, time available) you don't.
- Default to the safer, more auditable option. This is real money's shadow, even when it's paper.
