# ETF Universe — Approved Trading List

> Last updated: 2026-04-19
> Status: Pending compliance confirmation (open question #2 in docs/compliance.md)
>
> The bot may ONLY trade tickers on this list. Any ticker not listed here is implicitly restricted.
> Sector ETFs are excluded from the initial universe pending compliance review.

---

## Risk-On — Equity

| Ticker | Fund | Role | Notes |
|--------|------|------|-------|
| VTI | Vanguard Total Stock Market ETF | US equity core | Broadest US exposure; default equity holding |
| QQQ | Invesco Nasdaq-100 ETF | US large growth | High-conviction risk-on; higher beta |
| VIG | Vanguard Dividend Appreciation ETF | US quality / dividend growth | Moderate risk-on; lower volatility than VTI |
| VEA | Vanguard FTSE Developed Markets ETF | Developed international equity | Diversification away from US concentration |
| VWO | Vanguard FTSE Emerging Markets ETF | Emerging markets equity | Aggressive risk-on only; high volatility |

## Risk-On — Credit

| Ticker | Fund | Role | Notes |
|--------|------|------|-------|
| HYG | iShares iBoxx High Yield Corporate Bond ETF | High yield credit | Risk-on signal: spreads tightening |
| VNQ | Vanguard Real Estate ETF | US REITs | Risk-on / inflation hedge; rate-sensitive |

## Neutral / Transition

| Ticker | Fund | Role | Notes |
|--------|------|------|-------|
| BND | Vanguard Total Bond Market ETF | Total bond market | Default neutral holding; broad fixed income |
| LQD | iShares iBoxx Investment Grade Corporate Bond ETF | Investment grade credit | Mild risk-off; higher yield than treasuries |

## Risk-Off — Treasuries

| Ticker | Fund | Role | Notes |
|--------|------|------|-------|
| IEF | iShares 7-10 Year Treasury Bond ETF | Intermediate treasury | Core risk-off holding |
| TLT | iShares 20+ Year Treasury Bond ETF | Long-duration treasury | High-conviction risk-off; high rate sensitivity |
| SHY | iShares 1-3 Year Treasury Bond ETF | Short-duration treasury / cash proxy | Capital preservation in extreme risk-off |

## Inflation Hedges

| Ticker | Fund | Role | Notes |
|--------|------|------|-------|
| TIP | iShares TIPS Bond ETF | Inflation-protected treasuries | Hold when CPI trending up and regime is neutral/risk-off |
| GLD | SPDR Gold Shares ETF | Gold | Risk-off and inflation hedge; low correlation to equities |
| PDBC | Invesco Optimum Yield Diversified Commodity Strategy ETF | Broad commodities | Inflation and risk-on commodity cycle exposure |

---

## Tickers NOT on this list

Any ticker not in the table above — including individual stocks, leveraged ETFs, inverse ETFs, options, futures, and crypto — is prohibited. The guardrails layer enforces this in code; this file is the human-readable source of truth.

Sector ETFs (XLF, XLK, XLE, etc.) are intentionally excluded pending compliance confirmation that employer industry restrictions do not apply.

---

## Adding a new ticker

Before adding any ticker:
1. Check `guardrails/restricted.md` — if it appears there, do not add it.
2. Confirm with user: "Has compliance approved this specific ticker?"
3. Add below with a one-line rationale (asset class, portfolio role).
4. Note the addition in the next weekly review log.
