# ETF Universe — Approved Trading List

> **Source of truth**: `strategy/appendix_2_approved.json` — machine-readable list of every ETF approved under firm policy Appendix 2 (v2.1, 31-Mar-2026).
> **Restricted**: `guardrails/restricted.md` — Appendix 3 removals and bot-imposed restrictions.
> **This file**: human-readable curated view of tickers the strategy actively considers, organized by role. The *whitelist* is the JSON; this markdown is the *strategy's preferred shortlist*.

Last updated: 2026-04-27
Compliance status: Confirmed — firm rep explicitly approved Appendix 2 as the auto-trading universe.

---

## How the whitelist works

1. **Any ticker in `appendix_2_approved.json`** is eligible for trading.
2. **Any ticker in `guardrails/restricted.md`** is blocked, even if it appears in the JSON.
3. **Any ticker NOT in the JSON** is implicitly blocked.
4. The code in `skills/guardrails/checker.py` enforces this on every order.

Bot routines should prefer the curated shortlist below. Only deviate to other Appendix 2 tickers when the strategy has a clear reason (e.g., sector rotation, new regime, specific hedge).

---

## Curated shortlist by role

### Risk-On — Equity (broad)

| Ticker | Fund | Role |
|--------|------|------|
| VTI | Vanguard Total Stock Market ETF | US equity core (default) |
| VOO | Vanguard S&P 500 ETF | US large-cap alternative |
| SPY | SPDR S&P 500 | US large-cap liquid alternative |
| QQQ | Invesco Nasdaq-100 | US large growth, higher beta |
| QQQM | Invesco Nasdaq-100 (lower fee) | QQQ alternative for buy-and-hold |
| VB | Vanguard Small-Cap | Small-cap diversifier |
| IWM | iShares Russell 2000 | Small-cap alternative |

### Risk-On — Quality / Dividend

| Ticker | Fund | Role |
|--------|------|------|
| DGRO | iShares Core Dividend Growth | Quality / dividend growth, lower vol (VIG equivalent; VIG not on Appendix 2) |
| SCHD | Schwab US Dividend Equity | Dividend alternative |
| NOBL | ProShares S&P 500 Dividend Aristocrats | Long-history dividend growers |
| QUAL | iShares MSCI USA Quality Factor | Quality factor tilt |
| USMV | iShares MSCI USA Min Vol | Low-volatility equity |

### Risk-On — International

| Ticker | Fund | Role |
|--------|------|------|
| VEA | Vanguard FTSE Developed Markets | Developed international core |
| IEFA | iShares Core MSCI EAFE | Developed intl alternative |
| VXUS | Vanguard Total International Stock | Total ex-US |
| VWO | Vanguard FTSE Emerging Markets | Emerging markets (aggressive risk-on only) |
| IEMG | iShares Core MSCI Emerging Markets | EM alternative |

### Risk-On — Credit

| Ticker | Fund | Role |
|--------|------|------|
| HYG | iShares iBoxx High Yield Corporate Bond | High yield — spread-tightening signal |
| JNK | SPDR Bloomberg High Yield Bond | HY alternative |

### Neutral

| Ticker | Fund | Role |
|--------|------|------|
| BND | Vanguard Total Bond Market | Total bond market (default neutral) |
| AGG | iShares Core US Aggregate Bond | Total bond alternative |
| LQD | iShares iBoxx Investment Grade Corp | IG credit — mild risk-off |
| VCIT | Vanguard Intermediate-Term Corp | IG credit alternative |

### Risk-Off — Treasuries

| Ticker | Fund | Role |
|--------|------|------|
| IEF | iShares 7-10 Year Treasury | Intermediate treasury (core risk-off) |
| VGIT | Vanguard Intermediate Treasury | IEF alternative |
| TLT | iShares 20+ Year Treasury | Long duration — high conviction risk-off |
| SPTL | SPDR Long-Term Treasury | TLT alternative |
| SHY | iShares 1-3 Year Treasury | Short duration — capital preservation |
| VGSH | Vanguard Short-Term Treasury | SHY alternative |
| SGOV | iShares 0-3 Month Treasury | Cash equivalent |
| BIL | SPDR 1-3 Month T-Bill | Cash equivalent alternative |

### Inflation & Real Assets

| Ticker | Fund | Role |
|--------|------|------|
| TIP | iShares TIPS Bond | Inflation-protected treasuries |
| SCHP | Schwab US TIPS | TIPS alternative |
| VTIP | Vanguard Short-Term TIPS | Short-duration TIPS |
| GLD | SPDR Gold Trust | Gold — risk-off and inflation hedge |
| IAU | iShares Gold Trust | GLD alternative (lower expense) |
| GSG | iShares S&P GSCI Commodity | Broad commodities |
| DBA | Invesco DB Agriculture | Agricultural commodities |

### Municipal / Tax-Aware

| Ticker | Fund | Role |
|--------|------|------|
| MUB | iShares National Muni Bond | Tax-aware fixed income |
| VTEB | Vanguard Tax-Exempt Bond | Muni alternative |

---

## Out of scope for this strategy

The following are approved under Appendix 2 but excluded from active strategy consideration:

- **Crypto ETPs** (IBIT, FBTC, ETHA, etc.): Too volatile, no strategic role in regime-based rotation
- **Single-commodity funds** (USO, UGA, CORN, etc.): Too narrow; GSG/DBA give broader exposure
- **Innovator defined-outcome ETFs** (BJAN, PJAN, UJAN, etc.): Unusual payoff structures unsuitable for regime rotation
- **Volatility products** (VIXY, VXX): Contango decay makes them unsuitable — also explicitly restricted
- **Goldman Sachs proprietary ETFs** (GSLC, GSIE, etc.): Approved but defer to broader market equivalents unless specifically strategic

If a routine proposes any of these, it must cite a specific rule in `strategy/rules.md` justifying the choice.

---

## Adding a new ticker to the curated shortlist

Before adding any ticker:
1. Verify it exists in `strategy/appendix_2_approved.json`. If not, STOP — it is not approved.
2. Verify it is not in `guardrails/restricted.md`.
3. Add it above with role and one-line rationale.
4. Note the addition in the next weekly review log.

## Adding a ticker to the approved JSON

Only add to `appendix_2_approved.json` if the firm publishes a new Appendix 2 version. Reference the updated document date and version in the JSON's `last_updated` and `source` fields.
