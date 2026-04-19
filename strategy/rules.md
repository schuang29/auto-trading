# Trading Rules

> Plain-English rules the bot follows for entry, exit, and sizing.
> Every trade decision in `memory/decisions/` must cite the specific rule number that justified it.
> Hard limits (position caps, max trades/day) are enforced in code — see `guardrails/hard_limits.md`.

---

## 1. Universe constraint

**Rule 1.1** — The bot may only trade ETFs listed in `strategy/universe.md`. No exceptions.

**Rule 1.2** — Before placing any order, verify the ticker is not on `guardrails/restricted.md`. If it is, abort the order and log the block.

---

## 2. Regime-based target allocations

Target allocations are guidelines. Actual orders are sized to move toward the target, not to hit it exactly in one trade (see Rule 4 on position sizing).

### RISK-ON target portfolio

| Ticker | Target weight |
|--------|--------------|
| VTI | 30% |
| QQQ | 15% |
| VIG | 10% |
| VEA | 10% |
| VWO | 5% |
| HYG | 5% |
| VNQ | 5% |
| GLD | 5% |
| BND | 10% |
| IEF | 5% |

### NEUTRAL target portfolio

| Ticker | Target weight |
|--------|--------------|
| VTI | 20% |
| VIG | 10% |
| VEA | 5% |
| BND | 25% |
| IEF | 20% |
| TIP | 10% |
| GLD | 10% |

### RISK-OFF target portfolio

| Ticker | Target weight |
|--------|--------------|
| TLT | 30% |
| IEF | 25% |
| SHY | 15% |
| TIP | 10% |
| GLD | 15% |
| BND | 5% |

---

## 3. Entry rules

**Rule 3.1** — Only enter or increase a position on the day a regime is confirmed (second consecutive day of the new regime reading). Do not act on day 1 of a potential regime change.

**Rule 3.2** — Only trade during market hours (9:30 AM – 4:00 PM ET). The market-open routine executes at 9:35 AM ET to avoid the opening auction.

**Rule 3.3** — Use market orders for all entries and exits. ETFs on this list are liquid enough that limit orders are not necessary for the size we trade.

**Rule 3.4** — Do not open a new position in a ticker if the current paper holding period for that ticker is less than 30 days, unless a regime change requires it. This respects the assumed 30-day holding period compliance constraint.

---

## 4. Position sizing

**Rule 4.1** — No single position may exceed 30% of portfolio equity. The guardrail code enforces this hard cap before every order.

**Rule 4.2** — When rebalancing toward a new target, move in steps: rebalance at most 50% of the gap between current and target weight per trading session. This reduces market impact and avoids overtrading.

**Rule 4.3** — Minimum order size is $500 notional. Do not place orders smaller than this — the transaction cost and complexity are not worth it.

**Rule 4.4** — Maximum orders per day is 5 (across all tickers). If the rebalance requires more, prioritize the largest deviations from target.

---

## 5. Exit rules

**Rule 5.1** — Exit or reduce a position when the regime shifts away from the regime that justified the entry, and the new regime has been confirmed for 2 consecutive days.

**Rule 5.2** — Apply a 15% trailing stop on each position, measured from the position's high-water-mark since entry. If a position drops 15% from its peak, exit at market open the following day.

**Rule 5.3** — Do not partially exit a position solely to take profits. Profit-taking is handled by rebalancing (Rule 4.2) when the target weight drops. Emotion-based or arbitrary profit-taking is not a rule.

---

## 6. Cash management

**Rule 6.1** — Maintain a minimum 5% cash buffer at all times. Do not deploy 100% of equity.

**Rule 6.2** — If cash falls below 3% due to market movements, do not place any new buy orders until cash is restored above 5% (through dividends, ETF distributions, or a sell triggered by another rule).

---

## 7. No-trade conditions

**Rule 7.1** — Do not trade on any date listed in `guardrails/blackouts.md`.

**Rule 7.2** — Do not trade if the Alpaca API returns an error on account status. Log the error and abort the session.

**Rule 7.3** — Do not trade if the pre-market routine failed to produce a valid regime classification (e.g., data source outage). Log the failure and skip the market-open routine for that day.

---

## 8. Logging requirement

**Rule 8.1** — Every executed trade (paper or signal) must produce a file in `memory/decisions/` with:
- Ticker, side (buy/sell), quantity, price
- Regime at time of decision
- Rule number(s) that justified the trade
- Any override or unusual condition noted

A trade without a logged decision file is a compliance violation, even on paper.
