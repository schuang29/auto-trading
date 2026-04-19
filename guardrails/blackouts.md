# Trading Blackout Dates

> The bot will not place any orders on dates listed here.
> Enforced in code before every order.

Last updated: 2026-04-19

---

## Recurring blackouts — US market holidays

The bot skips trading on all NYSE market holidays. Alpaca's API returns market status; the market-open routine checks `is_open` before placing any order.

Standard NYSE holidays (no hardcoding needed — Alpaca API handles this):
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving Day
- Christmas Day

---

## Employer compliance blackouts

*(None yet — populate if employer specifies trading blackout windows, e.g., around earnings seasons or executive quiet periods.)*

| Start date | End date | Reason |
|------------|----------|--------|
| | | |

---

## Ad hoc blackouts

Use this section for one-off dates (e.g., you're traveling and want a manual review before any trades execute).

| Date | Reason |
|------|--------|
| | |
