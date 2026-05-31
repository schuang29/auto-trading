# 0009 — Wind down scheduled routines

**Date:** 2026-05-31
**Status:** Accepted

## Context

The bot has been running the full 5-routine schedule (pre-market, market-open, midday, EOD, weekly) plus a heartbeat dead-man's-switch since 2026-04-27. Two consecutive clean weeks (W21, W22) on benign tape produced correct-but-easy regime calls and zero trades — the cash-buffer + minimum-order-size rule stack has bound the bot into a structural no-trade state since W19. The W22 weekly review (`memory/weekly/2026-W22.md`) projected the deployable-cash lockout to reach ~$0 by mid-June at the current +1.4%/week appreciation rate, at which point the rule stack would be fully self-blocking.

Operator chose to pause autonomous operation rather than continue producing daily logs that document a stationary state. The unresolved strategy questions (cash-buffer lockout, Rule 4.2 vs 4.3 vs 6.1 interaction, log-write `@`/`$`-strip bug) remain on the table but do not need to be answered under the pressure of a live daily schedule.

## Decision

Delete all six `AutoTrading-*` Windows scheduled tasks (`PreMarket`, `MarketOpen`, `Midday`, `EOD`, `Weekly`, `Heartbeat`).

Leave untouched: the codebase, the Alpaca paper account and its positions, the GitHub repo, the `memory/` audit trail.

This is a deliberate operator decision, not a failure — `memory/health/ALERT-*.md` files should not be expected and their absence is not a signal.

## Consequences

- No autonomous runs after the 2026-05-29 EOD commit. No further pre-market briefs, market-open executions, midday checks, EOD summaries, weekly reviews, or heartbeat checks.
- Alpaca paper positions sit frozen at the 2026-05-29 EOD state (~$104,723 equity across 9 ETFs: BND, DGRO, GLD, HYG, IEF, QQQ, VEA, VTI, VWO). HWMs in `memory/highwatermarks.json` are frozen as of that date.
- The dead-man's-switch is gone, so the operator is now responsible for noticing if/when they want to resume. No email alert will fire if the bot is "missing" — because nothing expects it to run.
- Audit trail (`memory/`) remains intact and append-only per Rule 5. On resumption the next pre-market brief will see a multi-day gap between its "most recent prior daily log" reference and itself; that is expected behavior, not a regime-continuity break (signals are recomputed fresh each run).
- The `scripts/setup_scheduler.ps1` script is unchanged — re-running it from an elevated PowerShell fully restores the schedule. Reinstatement procedure is documented in `CLAUDE.md` § "Scheduled automation" and `docs/runbook.md` § "All scheduled tasks".
- PAT expiry watch item (~2027-05, per `memory/git-push-wincredman-failure.md`) is unaffected; if reinstating after that date the PAT must be rotated first.
