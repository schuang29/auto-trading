# Compliance Notes

> Open questions and answers as they arrive from employer compliance.
> Update this file when answers come in. If an answer changes the architecture, note it here and re-plan with the user.

Last updated: 2026-04-23

---

## Open questions

| # | Question | Default assumption | Status |
|---|---|---|---|
| 1 | Is Alpaca an approved broker for personal accounts (paper trading)? | Assume yes for paper; confirm before any real-money use | **Pending** |
| 2 | Does the ETF restriction require a defined whitelist, or is any ETF allowed? | Whitelist-based (conservative default) | **Resolved 2026-04-23** |
| 3 | Are there holding-period requirements (e.g., 30/60-day minimum)? | Assume 30 days | **Pending** |
| 4 | Is there a restricted ETF list (sector ETFs touching employer industry, etc.)? | `guardrails/restricted.md` is empty until confirmed | **Pending** |
| 5 | Are duplicate confirms / 407 letters required for ETF trades? | Note for Fidelity setup; no impact on Alpaca paper | **Pending** |
| 6 | Do blackout windows apply to ETF trades? | `guardrails/blackouts.md` has no employer blackouts yet | **Pending** |

---

## Answers received

### Question 2 — ETF whitelist
Date answered: 2026-04-23
Answer: Yes, a defined whitelist exists. Appendix 2 of the Personal Trading Policy (v2.1, March 31, 2026) lists all ETFs exempt from pre-clearance. Appendix 3 lists ETFs removed from Appendix 2 (no longer approved).
Impact: Trading universe locked to Appendix 2. VNQ (Vanguard Real Estate ETF) and PDBC (Invesco Commodity ETF) were not found in Appendix 2 and have been removed from strategy/universe.md. GSG (iShares S&P GSCI Commodity-Indexed Trust) added as Appendix 2-approved commodity replacement for PDBC. All other universe ETFs confirmed present in Appendix 2.
Action taken: strategy/universe.md updated (removed VNQ, removed PDBC, added GSG, updated status header). strategy/rules.md still references VNQ in RISK-ON target allocation — user decision pending on redistribution.

---

## Answer log format

```
### Question N — [topic]
Date answered: YYYY-MM-DD
Answer: [verbatim or paraphrased response from compliance]
Impact: [what changes in the bot as a result]
Action taken: [file updated, ADR written, etc.]
```
