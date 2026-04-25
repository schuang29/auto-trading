# Compliance Notes

> Open questions and answers as they arrive from employer compliance.
> Update this file when answers come in. If an answer changes the architecture, note it here and re-plan with the user.

Last updated: 2026-04-24

---

## Open questions

| # | Question | Default assumption | Status |
|---|---|---|---|
| 1 | Is Alpaca an approved broker for personal accounts (paper trading)? | Assume yes for paper; confirm before any real-money use | **Pending** |
| 2 | Does the ETF restriction require a defined whitelist, or is any ETF allowed? | Whitelist-based (conservative default) | **Resolved 2026-04-24** |
| 3 | Are there holding-period requirements (e.g., 30/60-day minimum)? | Assume 30 days | **Pending** |
| 4 | Is there a restricted ETF list (sector ETFs touching employer industry, etc.)? | Populated from Appendix 3 | **Resolved 2026-04-24** |
| 5 | Are duplicate confirms / 407 letters required for ETF trades? | Note for Fidelity setup; no impact on Alpaca paper | **Pending** |
| 6 | Do blackout windows apply to ETF trades? | `guardrails/blackouts.md` has no employer blackouts yet | **Pending** |

---

## Answers received

### Question 2 — ETF whitelist
Date answered: 2026-04-24 (superseding initial 2026-04-23 assumption)
Answer: Yes, a defined whitelist exists. Appendix 2 of the firm's Personal Trading Policy (v2.1, 31-Mar-2026) lists all ETFs exempt from pre-clearance. Appendix 3 lists ETFs removed from Appendix 2 (no longer approved). User confirmed directly with firm rep.
Impact: Trading universe locked to Appendix 2 (USA-region tickers). Full Appendix 2 approved list has been encoded in `strategy/appendix_2_approved.json` as the machine-readable source of truth. `strategy/universe.md` now references this file and presents a curated shortlist for active strategy use. `skills/guardrails/checker.py` loads and enforces against the JSON — any ticker not in it is blocked at the code level.
Action taken:
- Created `strategy/appendix_2_approved.json` with all ~230 USA-region approved tickers organized by category
- Rewrote `strategy/universe.md` to reference the JSON and provide a curated shortlist
- Updated `skills/guardrails/checker.py` to load and enforce against the JSON whitelist
- Updated `guardrails/restricted.md` with all Appendix 3 explicitly-removed tickers plus bot-imposed restrictions (VIXY, VXX, SH)

### Question 4 — Restricted ETF list
Date answered: 2026-04-24
Answer: The firm maintains Appendix 3 ("List of ETFs and Indices Removed from Appendix 2") which functions as the explicit restricted list for auto-trading. Tickers appearing in Appendix 3 have been actively removed from the approved list and must not be traded.
Impact: All Appendix 3 tickers are loaded into `guardrails/restricted.md` and enforced by the guardrails checker. Notable removals include VUG, IWF, IVW, IUSG, OEF (growth ETFs), DIA (Dow), XLF/XLU (sector SPDRs), IYR (real estate), UPRO (leveraged), EWG/EWU (single-country), and others.
Action taken: `guardrails/restricted.md` updated with 18 Appendix 3 removals plus 3 bot-imposed restrictions.

---

## Answer log format

```
### Question N — [topic]
Date answered: YYYY-MM-DD
Answer: [verbatim or paraphrased response from compliance]
Impact: [what changes in the bot as a result]
Action taken: [file updated, ADR written, etc.]
```
