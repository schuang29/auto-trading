# Regime Classification

> The bot classifies the market into one of three regimes before each trading session.
> Regime determines the target allocation from `rules.md`.
> All three signals must be evaluated; majority rules.

---

## Signals

### Signal 1 — Trend (SPY vs 200-day SMA)

| Condition | Vote |
|-----------|------|
| SPY closing price > 200-day SMA | Risk-On |
| SPY closing price ≤ 200-day SMA | Risk-Off |

Data source: Alpaca Data API or yfinance (SPY daily close).

### Signal 2 — Volatility (VIX level)

| Condition | Vote |
|-----------|------|
| VIX < 20 | Risk-On |
| 20 ≤ VIX ≤ 25 | Neutral |
| VIX > 25 | Risk-Off |

Data source: yfinance (^VIX daily close). If VIX data is unavailable, this signal is skipped and the other two determine regime.

### Signal 3 — Yield Curve (10yr minus 2yr spread)

| Condition | Vote |
|-----------|------|
| 10yr − 2yr > 0 (normal curve) | Risk-On |
| 10yr − 2yr = 0 to −0.25 (flat) | Neutral |
| 10yr − 2yr < −0.25 (inverted) | Risk-Off |

Data source: FRED via yfinance (^TNX for 10yr, ^IRX for 13-week as 2yr proxy) or direct FRED API.

---

## Regime determination

Count Risk-On, Neutral, Risk-Off votes across all available signals:

| Outcome | Regime |
|---------|--------|
| 2+ Risk-On votes | **RISK-ON** |
| 2+ Risk-Off votes | **RISK-OFF** |
| Majority Neutral, or split | **NEUTRAL** |

---

## Regime change rules

- A regime change only takes effect if the new regime has held for **2 consecutive trading days**. This prevents whipsawing on a single volatile day.
- When regime changes, log the transition to `memory/daily/YYYY-MM-DD.md` with all three signal values.
- Do not trade on the day a regime change is first detected — wait for confirmation the next day. On confirmation day, rebalance toward the new target allocation.

---

## Regime log format

Each pre-market routine records:

```
Regime: RISK-ON | RISK-OFF | NEUTRAL
  SPY vs 200d SMA: [price] vs [SMA] → Risk-On / Risk-Off
  VIX: [value] → Risk-On / Neutral / Risk-Off
  10yr-2yr spread: [value]% → Risk-On / Neutral / Risk-Off
  Confirmed: yes / no (day 1 of potential change)
```
