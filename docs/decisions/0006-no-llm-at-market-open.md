# ADR-0006: No LLM at market-open

Date: 2026-04-27
Status: Accepted

## Context

Four of the bot's five scheduled routines are LLM-driven: pre-market, midday, EOD, and weekly review. Each follows a markdown prompt in `routines/` and uses Claude to read context, fetch data, and produce a written summary plus state updates.

Market-open is the exception. It's a pure-Python script (`scripts/market_open.py`) that reads a JSON proposal file, runs each proposed order through the guardrail checker, and submits to Alpaca paper. No LLM is in the loop between 9:30 AM ET (the moment pre-market's plan is finalized) and 9:35 AM ET (the moment orders hit Alpaca).

This was a deliberate architectural choice that's worth documenting since it diverges from the "bot is Claude Code on cron" model used elsewhere.

## Decision

**Market-open is pure Python and contains no LLM call. The orders to place are fully specified by pre-market in `memory/proposals/YYYY-MM-DD.json`. Market-open's job is execution, not decision-making.**

## Consequences

**Why this is the right design:**

- **Decisions and execution are separated in time.** Pre-market runs at 7:30 AM ET and has ~2 hours of clock time and full LLM reasoning budget to draft proposals, weigh trade-offs, and cite specific rules. By 9:35 AM ET the *thinking* is done; what remains is mechanical execution. There is nothing for an LLM to add at that step that pre-market hasn't already done.
- **Speed.** The market-open routine completes in 5–10 seconds. An LLM call would take 30–120 seconds, all of it during the most price-sensitive minutes of the trading day. The opening auction is a poor moment to be slow.
- **Determinism.** Given the same proposal JSON and the same Alpaca account state, the script produces the same orders every time. This is correct behavior for an executor: the strategy decides, the executor executes. If two runs of market-open produced different orders from the same input, that would be a bug.
- **Cost.** Saving one Claude call per day is minor on its own (~$0.10). Saving it across 250 trading days per year is $25; not material. But the cost benefit is the small one — the architectural benefit is the large one.
- **Testability.** A pure-Python script with mocked Alpaca responses can be tested deterministically (see `tests/test_market_open.py`). LLM-in-the-loop testing requires either expensive cassette-style replay infrastructure or accepting flaky tests.
- **Failure modes are easier to reason about.** If market-open fails, the failure is in code: a missing proposals file, a guardrail block, or an Alpaca API error. Each is a specific class of fault with a specific recovery path. An LLM-driven market-open could fail in many additional ways (API timeout, prompt-injection-style hallucination, model unavailability) that are harder to diagnose at 9:35 AM.

**What we lose:**

- **No reasoning at execution time.** If overnight news invalidates a proposal between 7:30 AM and 9:35 AM, market-open will still execute the original plan unmodified. The mitigation is upstream: pre-market is responsible for producing proposals that account for the most current information available. If pre-market's view ever needs to change post-7:30 AM, the right move is to *regenerate the proposal file* (manually or via a re-run), not to give market-open the ability to second-guess.
- **LLM-flagged compliance issues at 7:30 AM are not re-checked at 9:35 AM.** For example, the W17 VIG/DGRO compliance flag was caught by pre-market and the proposal was modified before market-open ran. If pre-market had failed to catch it, market-open would have submitted the order (until the guardrail caught it at the code level). The guardrail layer is the safety net here, not the LLM.

**When this design *would* break down:**

- **If proposals ever need real-time conditional logic** (e.g., "buy VTI only if SPY is below $710 at 9:35"), the design either needs a proposal-format extension or needs an LLM step. Currently no such logic exists; if it ever does, this ADR should be revisited.
- **If the bot is ever given execution authority over individual stocks or options** (compliance currently prohibits both), more nuanced execution decisions might warrant LLM-in-the-loop. Not relevant within current constraints.

**Related design choices:**

- The pre-market routine writes `memory/proposals/YYYY-MM-DD.json` as its execution contract. This file is effectively the API between the LLM-driven decision phase and the deterministic execution phase. Its schema is informally specified in `routines/pre_market.md` and consumed by `scripts/market_open.py`. Worth formalizing as a JSON schema if the format ever needs to change.
- The five-routine model is described in `PLAN.md` §5. Market-open being pure Python is the only routine where the prompt-in-`routines/`-folder pattern doesn't apply. That asymmetry is intentional and now documented.
