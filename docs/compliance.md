# Compliance Notes

> Open questions and answers as they arrive from employer compliance.
> Update this file when answers come in. If an answer changes the architecture, note it here and re-plan with the user.

Last updated: 2026-04-19

---

## Open questions

| # | Question | Default assumption | Status |
|---|---|---|---|
| 1 | Is Alpaca an approved broker for personal accounts (paper trading)? | Assume yes for paper; confirm before any real-money use | **Pending** |
| 2 | Does the ETF restriction require a defined whitelist, or is any ETF allowed? | Whitelist-based (conservative default) | **Pending** |
| 3 | Are there holding-period requirements (e.g., 30/60-day minimum)? | Assume 30 days | **Pending** |
| 4 | Is there a restricted ETF list (sector ETFs touching employer industry, etc.)? | `guardrails/restricted.md` is empty until confirmed | **Pending** |
| 5 | Are duplicate confirms / 407 letters required for ETF trades? | Note for Fidelity setup; no impact on Alpaca paper | **Pending** |
| 6 | Do blackout windows apply to ETF trades? | `guardrails/blackouts.md` has no employer blackouts yet | **Pending** |

---

## Answers received

*(None yet — update below as responses come in.)*

---

## Answer log format

```
### Question N — [topic]
Date answered: YYYY-MM-DD
Answer: [verbatim or paraphrased response from compliance]
Impact: [what changes in the bot as a result]
Action taken: [file updated, ADR written, etc.]
```
