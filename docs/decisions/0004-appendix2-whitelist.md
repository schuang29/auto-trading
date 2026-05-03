# ADR-0004: JSON whitelist + markdown shortlist for the trading universe

Date: 2026-04-24
Status: Accepted

## Context

On 2026-04-24, the firm's compliance team confirmed that personal ETF trading must be restricted to the list in Appendix 2 of the firm's Personal Trading Policy. Appendix 2 contains ~230 USA-region tickers spanning broad market, sector, factor, fixed-income, commodity, and other ETF categories. Appendix 3 lists tickers explicitly removed from Appendix 2 over time.

The bot needs two distinct things from the universe:
1. **Hard enforcement** — a guardrail that blocks any order on a ticker not on Appendix 2.
2. **Strategy guidance** — a much smaller curated shortlist (~15 tickers) that the regime strategy actively considers, with each ticker labeled by role (US equity core, dividend tilt, intermediate Treasury, etc.).

Three options were considered:
- **JSON only** — encode all 230 tickers in JSON, have the strategy reference the JSON directly.
- **Markdown only** — encode all 230 tickers in `strategy/universe.md` as a flat list, with the curated subset highlighted somehow.
- **Hybrid** — JSON for the full whitelist, markdown for the curated shortlist with role labels.

## Decision

**Hybrid. The authoritative whitelist lives in `strategy/appendix_2_approved.json`. The curated shortlist with strategic role labels lives in `strategy/universe.md`. The guardrail (`skills/guardrails/checker.py`) enforces against the JSON, not the markdown.**

## Consequences

**Why this works:**
- **The JSON is the source of truth, full stop.** When a guardrail blocks a ticker, the rejection cites `strategy/appendix_2_approved.json` directly. There's no ambiguity about whether the markdown was out of date.
- **The JSON is machine-checkable.** When the firm publishes a new Appendix 2 version, we can diff the JSON before/after and produce a clear summary of additions and removals. This is much harder against a markdown table.
- **The markdown is for humans (and the LLM as a strategy author).** Reading 230 tickers in JSON is hostile; reading 15 with one-line role descriptions is informative. The bot's pre-market routine reads `strategy/universe.md` to pick proposals, then the guardrail validates the picks against the JSON.
- **The two files cannot drift in a dangerous direction.** A ticker could appear in the markdown but not the JSON — which means the guardrail would block it (safe failure mode). The reverse — JSON has it but markdown doesn't — just means the strategy doesn't actively consider it, which is fine.

**Why JSON, not YAML or TOML, for the whitelist:**
- Python's stdlib reads JSON natively (no extra dependency).
- The data shape is a flat ticker list; YAML/TOML's flexibility isn't needed.
- JSON's lack of comments is a non-issue here — provenance lives in the file's `last_updated` and `source` keys.

**Why markdown, not JSON, for the shortlist:**
- Each ticker has a one-line description of its strategic role. Prose is the right format for prose.
- The shortlist is grouped by role (Risk-On Equity, Quality, Treasuries, etc.). Markdown headers express this naturally.
- The LLM reads `strategy/universe.md` during pre-market and reasons about which roles to fill given the current regime. JSON would require the LLM to reconstruct the structure from a flat list.

**Restricted tickers:**
The Appendix 3 removals (and bot-imposed restrictions like VIXY/VXX/SH for being inappropriate to the strategy) live in `guardrails/restricted.md`. The guardrail checks both: a ticker must be in the JSON whitelist AND not in the restricted markdown. This split is principled — the JSON is "what the firm allows," the markdown is "what we additionally choose not to trade." Mixing the two would obscure where each restriction came from.

**Updating the whitelist when the firm publishes a new Appendix 2:**
1. Save the new policy PDF to `docs/compliance_source/`.
2. Diff the new approved-ticker list against the JSON.
3. Update the JSON in a single commit with the new `last_updated` and `source` version.
4. Move newly removed tickers into `guardrails/restricted.md` if Appendix 3 has expanded.
5. Note any added tickers worth promoting into the curated shortlist; default behavior is to leave the shortlist unchanged.

This process keeps compliance updates auditable as discrete commits.
