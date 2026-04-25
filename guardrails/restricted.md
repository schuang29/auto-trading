# Restricted ETF List

> The bot will never trade any ticker listed here, regardless of what a routine prompt suggests.
> This list is enforced in code before every order.
> This list supplements `strategy/appendix_2_approved.json` — any ticker not in that JSON is *implicitly* restricted; tickers below are *explicitly* restricted because the firm actively removed them from the approved list.

Last updated: 2026-04-24
Source: FIRMWIDE ANNEX - PERSONAL TRADING POLICY APPENDIX 3 (v2.1, 31-Mar-2026)

---

## Appendix 3 — Explicitly removed from approved list

These tickers were previously approved but have been removed by the firm. They MUST NOT be traded even if they appear on a data source as tradable or if a model suggests them.

| Ticker | Reason | Date removed |
|--------|--------|--------------|
| AAXJ | Appendix 3 removal (iShares MSCI All Country Asia ex Japan) | 2024-12-20 |
| BBAX | Appendix 3 removal (JPMorgan BetaBuilders Developed Asia ex-Japan) | 2023-11-09 |
| BKLN | Appendix 3 removal (Invesco Senior Loan ETF) | 2022-05-24 |
| DIA | Appendix 3 removal (SPDR Dow Jones Industrial Average) | 2022-10-22 |
| DTN | Appendix 3 removal (WisdomTree Dividend ex-Financials) | 2022-05-24 |
| ELD | Appendix 3 removal (WisdomTree Emerging Market Local Debt) | 2023-11-09 |
| ESGV | Appendix 3 removal (Vanguard ESG US Stock ETF) | 2023-11-09 |
| EWG | Appendix 3 removal (iShares MSCI Germany) | 2016-02-05 |
| EWU | Appendix 3 removal (iShares MSCI United Kingdom) | 2023-11-09 |
| IUSG | Appendix 3 removal (iShares Core US Growth) | 2023-11-09 |
| IVW | Appendix 3 removal (iShares S&P 500 Growth) | 2023-11-09 |
| IWF | Appendix 3 removal (iShares Russell 1000 Growth) | 2023-11-09 |
| IYR | Appendix 3 removal (iShares Dow Jones US Real Estate) | 2016-02-05 |
| OEF | Appendix 3 removal (iShares S&P 100) | 2023-11-09 |
| UPRO | Appendix 3 removal (ProShares UltraPro S&P 500 - leveraged) | 2021-12-11 |
| VUG | Appendix 3 removal (Vanguard Growth Index) | 2023-11-09 |
| XLF | Appendix 3 removal (Financial Select Sector SPDR) | 2016-02-05 |
| XLU | Appendix 3 removal (Utilities Select Sector SPDR) | 2016-02-05 |

---

## Bot-imposed additional restrictions

Beyond Appendix 3, the bot will not trade the following even if they appear in the approved list, because they are unsuitable for this strategy:

| Ticker | Reason | Date added |
|--------|--------|------------|
| VIXY | Volatility product — decay characteristics make it unsuitable for regime-based holding | 2026-04-24 |
| VXX | Volatility ETN — decay characteristics make it unsuitable for regime-based holding | 2026-04-24 |
| SH | Inverse S&P 500 — bot policy is long-only; no short exposure | 2026-04-24 |

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
