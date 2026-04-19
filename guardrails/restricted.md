# Restricted ETF List

> The bot will never trade any ticker listed here, regardless of what a routine prompt suggests.
> This list is enforced in code before every order.

Last updated: 2026-04-19
Reason for current state: Awaiting compliance response (see docs/compliance.md, question #4).

---

## Restricted tickers

*(None yet — list will be populated once compliance responds with any restricted ETFs, particularly sector ETFs that may touch employer industry.)*

---

## How to add a restriction

1. Add the ticker and reason below.
2. Update the "Last updated" date above.
3. Commit with message `guardrails: restrict TICKER — reason`.
4. The code reads this file at runtime; no code change required.

## Format

```
| TICKER | Reason | Date added |
```

| Ticker | Reason | Date added |
|--------|--------|------------|
