# ADR-0005: Half-step rebalance sizing (Rule 4.2)

Date: 2026-04-19
Status: Accepted

## Context

When the bot identifies a regime and the current portfolio differs from the regime's target allocation, it needs to decide how aggressively to close the gap.

Three approaches were considered:

- **Hit target in one trade.** If the target says VTI = 30% and current is 20%, place an order to bring VTI to exactly 30% on the next trading session.
- **Half-step (50% of the gap).** Each session, close half the distance between current and target. Repeat until close to target.
- **Fixed-amount step.** Each session, move a fixed dollar amount toward target regardless of gap size.

## Decision

**Half-step. Rule 4.2 of `strategy/rules.md`: "When rebalancing toward a new target, move in steps: rebalance at most 50% of the gap between current and target weight per trading session."**

## Consequences

**Why half-step:**

- **Reduces market impact at the bot's scale.** With ~$100k of paper capital this is mostly academic, but the strategy is meant to scale to a real Fidelity portfolio (Phase 5+). At larger sizes, putting a full target weight on in one print is a recipe for slippage.
- **Buys time for the regime call to be wrong.** Regime classification has a non-zero error rate. If the bot calls RISK-ON on Monday and would deploy 100% on Monday's open, a Tuesday flip costs a lot. Deploying 50% Monday and 25% Tuesday and 12.5% Wednesday gives the regime classifier multiple chances to correct itself before the bot is fully committed.
- **Avoids whipsaw losses on regime flips.** The exit side of half-step works the same way: if the regime flips back to NEUTRAL, the bot has only deployed ~75% of the target after a few sessions, so the round-trip cost of a false signal is much smaller than a full deployment would be.
- **Naturally interacts with the daily 5-trade cap (Rule 4.4).** With 9 ETFs in the RISK-ON portfolio and 5 trades per day, full deployment in one session would be impossible anyway. Half-step makes the gradual ramp explicit and intentional rather than an artifact of the trade cap.

**What it costs:**

- **Slow ramp from cash.** The first execution week (2026-04-27 → 05-01) took 5 sessions to go from 100% cash to ~87% deployed, with daily notional shrinking each day ($35k → $22.5k → $14.1k → $8.75k → $6.5k). A reader expecting "Monday open: full target weight" finds that surprising. The W18 weekly review noted this and flagged "is the user comfortable with this cadence?" as an open question.
- **Lag on regime entry.** When a clear new regime emerges, the bot is most under-invested at exactly the moment it most wants to be invested. Conversely, on regime exit, it's still 50%+ deployed when it most wants to be out.
- **Math interaction with Rule 4.1's 30% per-position cap.** When a target is at the cap (e.g., VTI target = 30%, cap = 30%), half-step asymptotically approaches the cap but never quite reaches it. This was originally a non-issue when VTI's target was 32.5%, but the target was lowered to 30% on 2026-05-02 (see `strategy/rules.md` §2 note) which makes the asymptotic-approach behavior the *only* way VTI can reach its target in steady state. Acceptable.

**Alternatives reconsidered post-launch:**

- **Adaptive step size based on volatility.** In low-VIX environments, take larger steps; in high-VIX environments, smaller. Has theoretical appeal. Rejected for v1 — adds complexity without a clear performance signal yet, and we want a clean baseline first. Reconsider after Phase 6 backtesting.
- **Asymmetric step size for entry vs exit.** Deploy slowly, exit quickly. Theoretically attractive (drawdown protection matters more than upside capture), and many practitioner strategies do this. Rejected for v1 to keep the rule symmetric and easy to audit. Strong candidate for a Phase 6 revision if the live data shows asymmetric regret.

**Falsification criteria:** if half-step produces consistently worse risk-adjusted returns than a "full deployment in one session" baseline over 60+ days of paper trading, the rule should be revisited. Track this as part of the weekly review.
