# Hard Limits

> These limits are enforced in code (`skills/guardrails/`) before every order reaches Alpaca.
> They cannot be overridden by a routine prompt. If a proposed trade violates a limit, it is rejected.
> See `strategy/rules.md` for the trading rules these limits protect.

---

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max position size | 30% of portfolio equity | Prevents catastrophic concentration in any single ETF |
| Min position size | $500 notional | Avoids trivially small orders that generate noise without meaningful exposure |
| Max orders per day | 5 | Limits overtrading; forces prioritization of the most impactful rebalances |
| Min cash buffer | 5% of portfolio equity | Ensures liquidity for unexpected rebalance needs |
| Min holding period | 30 days per ticker | Respects assumed compliance constraint; subject to update when employer confirms |
| Trailing stop | 15% from position high-water mark | Protects against large drawdowns in individual positions |
| Whitelist enforcement | Universe = `strategy/universe.md` | Any ticker not on the list is rejected, no exceptions |
| Restricted list check | Block list = `guardrails/restricted.md` | Any ticker on the list is rejected, no exceptions |
| Blackout enforcement | Dates = `guardrails/blackouts.md` | No orders placed on blackout dates |
| Market hours only | 9:30 AM – 4:00 PM ET | No pre-market or after-hours orders |
| Paper only | `ALPACA_BASE_URL` must contain `paper` | Code asserts this at startup; aborts if live credentials are detected |

---

## Enforcement model

Every order passes through a guardrail check function before submission. The check is a sequential gate:

1. Assert paper environment
2. Check blackout dates
3. Check market hours
4. Verify ticker on whitelist
5. Verify ticker not on restricted list
6. Check proposed position size ≤ 30% of equity
7. Check order notional ≥ $500
8. Check daily order count < 5
9. Check cash buffer will remain ≥ 5% after fill
10. Check holding period ≥ 30 days (unless selling)

If any check fails, the order is rejected, the reason is logged, and execution continues with the next proposed order (not a full abort).
