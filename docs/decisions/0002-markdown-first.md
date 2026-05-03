# ADR-0002: Markdown-first for strategy, rules, and memory

Date: 2026-04-19
Status: Accepted

## Context

The bot needs persistent storage for several distinct kinds of information:

- **Strategy specification** — the universe of approved tickers, target allocations per regime, rule definitions, regime classification logic, and the underlying thesis.
- **Operational guardrails** — hard limits the bot must never violate, restricted tickers, blackout dates.
- **Routines** — the prompts and procedures each scheduled routine follows.
- **Memory / audit trail** — every trade decision, daily log, weekly review, and current position state.

There were three plausible storage formats: a relational database (SQLite or Postgres), JSON config files, or markdown documents. The choice affects how the LLM reads, reasons about, and writes the bot's own state.

## Decision

**Markdown for everything that the LLM needs to read, reason about, or write in natural language. JSON only for machine-to-machine data (the Appendix 2 ticker whitelist, the high-water-mark snapshot, the daily proposals queue). CSV for time-series data (Phase 7 — see ADR-0003).**

The agent runtime is a language model. Markdown is its native I/O format. Strategy rules written as plain English prose ("If VIX > 25 and SPY is below its 200-day SMA, classify as RISK-OFF") are read, followed, and amended by the LLM far more reliably than the same rules expressed as JSON config or as functions in code.

## Consequences

**Why this works:**
- **Writing strategy rules is a writing task, not a programming task.** Plain prose lets the strategy author express intent directly, including edge cases ("topping up an existing position is not 'opening a new position' and is permitted") that would be awkward to encode in either JSON or code.
- **Audit trail is human-readable by default.** A reviewer (compliance, future-self, anyone) opens `memory/decisions/2026-04-28-0935-VTI-BUY.md` and immediately understands what happened and why. No SQL query needed.
- **Diffing is meaningful.** Markdown changes show up cleanly in `git diff`. Rule revisions become legible commit history rather than opaque database migrations.
- **The LLM amends its own rules correctly.** Asking Claude Code to "update Rule 4.2 to say 50% of the gap" works in markdown; in code it would require parsing intent into syntactically valid changes and risking a regression.
- **No schema migration cost.** Adding a column to a daily log is a sentence; adding a column to a SQL table is a migration script.

**What we give up:**
- **No native query language.** Asking "what was the average position size of all VTI buys in April?" requires either parsing markdown with regex or maintaining a derived structured view. Mitigated by Phase 7's CSV time-series, which captures exactly the queryable subset that matters.
- **Concurrent writes are unsafe.** Two routines writing to the same markdown file simultaneously will corrupt it. Mitigated by sequencing: routines run on schedule, never concurrently, and `memory/positions.md` is owned by one routine at a time.
- **No referential integrity.** Nothing prevents a decision file from citing a non-existent rule. Mitigated by tests that grep `memory/decisions/` for cited rule numbers and verify each exists in `strategy/rules.md`.

**Where we *don't* use markdown:**
- `strategy/appendix_2_approved.json` — the firm's whitelist is a flat ticker list, not prose. JSON is the right format. See ADR-0004.
- `memory/highwatermarks.json` — per-ticker peak prices read and written by code with no LLM involvement. JSON is appropriate.
- `memory/proposals/YYYY-MM-DD.json` — pre-market produces a structured proposal list consumed by the pure-Python market-open script. No reasoning between handoff, so JSON.
- `memory/timeseries/*.csv` — append-only daily numerical data. See ADR-0003.

**The split is principled, not arbitrary:** markdown when an LLM is in the loop reading or writing the file, structured formats when only code touches it.
