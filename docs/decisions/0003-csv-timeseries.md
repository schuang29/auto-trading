# ADR-0003: CSV for time-series data

Date: 2026-04-28
Status: Accepted

## Context

Phase 7 of the project plan called for daily capture of three data streams:

1. Portfolio state (equity, cash, daily P&L, cumulative P&L)
2. Per-position daily snapshots (ticker, quantity, avg cost, market value, weight)
3. Benchmark closes and returns (SPY, AGG, 60/40 blend, VT)

This data needs to be:
- Written by the EOD routine on every trading day
- Read by the weekly review routine for performance attribution
- Read by the future Phase 8 dashboard
- Auditable — a reviewer should be able to verify the numbers independently
- Survivable — append-only, with no possibility of accidental destruction

Four storage formats were considered: CSV, JSON, SQLite, Parquet.

## Decision

**CSV for all three time-series files: `memory/timeseries/portfolio_daily.csv`, `positions_daily.csv`, `benchmarks_daily.csv`.**

## Consequences

**Why CSV wins:**
- **Trivial round-trip.** `pandas.read_csv()` and Python's stdlib `csv` module both read and write these files in one line. No schema definition, no migration, no driver, no connection string.
- **Auditable in `git diff`.** When the EOD routine appends today's row, the diff shows exactly which row was added. Compare to a SQLite database, where the diff is unreadable binary.
- **Append-only is natural.** The data model is "one row per day per entity" with no updates after the fact. CSV's append semantics match the intent perfectly.
- **Spreadsheet-compatible.** Open in Excel, Numbers, Google Sheets, or any text editor. Useful for ad-hoc analysis without writing code.
- **Version control plays nicely.** A daily commit of the EOD routine adds a single new line per CSV. Repository size grows linearly and slowly. After 5 years of daily writes, the portfolio CSV will be ~100KB.

**What we considered and rejected:**

- **JSON.** Acceptable for nested or hierarchical data, but flat time-series is a tabular shape, not a tree. JSON would force an array-of-objects with redundant keys per row, bloating the file 5–10x and producing noisier diffs.
- **SQLite.** Would give us proper queries and indexes. But the data volume doesn't need it (a few hundred rows per year per file), and the binary format defeats `git diff`. Pandas can already query CSV-loaded DataFrames adequately. Adding a SQL layer is operational complexity without payoff at this scale.
- **Parquet.** Excellent for analytical workloads and compresses well. Wrong for our scale (overkill for kilobytes of data) and not human-readable, which loses the audit-trail benefit.

**Conventions enforced by the recorder:**
- All `_pct` columns are stored as decimal ratios. `0.0123` means 1.23%, not 123%. This is consistent across all three CSVs.
- Idempotency: writing for an existing date overwrites that day's rows; never duplicates. Re-running EOD on the same day is safe. Implemented in `skills/timeseries/recorder.py`.
- Sort order is deterministic (`(date, ticker)` for positions, `(benchmark, date)` for benchmarks). Enables clean diffs and correct cumulative-return computation.
- The 60/40 blend's `close_price` is intentionally empty — the blend has no underlying price, only daily-rebalanced returns computed from SPY and AGG dailies.

**Known weaknesses and mitigations:**
- **No type enforcement.** A bug could write `"N/A"` into a numeric column. Mitigated by `tests/test_timeseries.py` (17 tests covering math correctness, schema validation, and idempotence).
- **Concurrent writes will corrupt the file.** Same mitigation as ADR-0002: routines run on a schedule, never concurrently.
- **Silent write failures.** If the recorder raises during `eod.py`, the routine could log "completed successfully" while leaving a gap in the CSV. Mitigated 2026-05-02 by adding a post-write verification check in `eod.py` that re-reads the CSV and confirms today's row landed.
- **Phase 7 ship gap.** The recorder shipped on 2026-04-28; the bot's first execution day was 2026-04-27, so Monday's row was missing from `portfolio_daily.csv` until backfilled manually on 2026-05-02. The post-write verification check prevents this class of issue going forward.

**Phase 8 implications:** the dashboard reads these CSVs directly with pandas. No intermediate database needed. If the data scale ever exceeds CSV's comfortable range (~50k rows), revisit — but at one row per trading day, that's ~200 years of operation.
