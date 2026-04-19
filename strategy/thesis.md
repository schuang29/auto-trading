# Strategy Thesis

> Why this strategy is expected to work, and what would falsify it.

---

## Core idea

Markets cycle between risk-on and risk-off regimes that persist long enough to be exploitable. A simple three-signal regime classifier (trend, volatility, yield curve) can identify these regimes with enough lead time to rotate a diversified ETF portfolio into the appropriate posture before conditions deteriorate significantly.

This is tactical asset allocation, not stock-picking. The edge is not predicting individual assets — it is predicting the *environment* those assets will operate in, and holding the assets best suited to that environment.

---

## Why it should work

**1. Regime persistence.** Risk-off regimes historically last weeks to months, not days. A two-day confirmation rule trades some responsiveness for a large reduction in whipsaws. The cost is entering a bit late; the benefit is not being shaken out of positions by noise.

**2. Diversification within regimes.** The risk-on portfolio is not 100% equities. Holding GLD, BND, and HYG alongside VTI and QQQ reduces drawdown without dramatically cutting upside participation. The risk-off portfolio is not 100% cash. TLT and GLD have historically appreciated when equities fall sharply.

**3. Low turnover, low cost.** ETFs have near-zero spreads and low expense ratios. The 30-day minimum holding period assumption forces patience. Fewer trades = lower slippage and fewer opportunities for emotional decisions.

**4. Auditability.** Every decision has a cited rule. If the strategy underperforms, we can trace exactly which rules produced which outcomes and adjust them deliberately — not by gut feel.

---

## What would falsify this strategy

- The three regime signals produce no better than random outcomes over a 90-day paper period.
- The strategy trails a simple 60/40 (VTI/BND) buy-and-hold over the paper period by more than 2% annualized without a plausible explanation tied to an unusual macro environment.
- Regime changes come too late to avoid >20% drawdowns that a simpler strategy would have avoided.

If any of the above occurs, the strategy is revisited in a weekly review before continuing to signal Fidelity trades.

---

## What this strategy does NOT claim

- It does not claim to predict short-term price movements.
- It does not claim to beat the market every year.
- It does not claim to be optimal. It claims to be *auditable, compliant, and good enough* to beat a static allocation over a full market cycle.
