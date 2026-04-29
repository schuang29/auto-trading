"""
Backfill benchmarks_daily.csv from BACKFILL_START through yesterday.

Idempotent — safe to re-run. The recorder dedupes on (date, benchmark) and
recomputes daily/cumulative returns across the full series on every write.

Usage:
    python scripts/backfill_benchmarks.py
    python scripts/backfill_benchmarks.py --start 2026-04-19 --end 2026-04-27
    python scripts/backfill_benchmarks.py --dry-run
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.timeseries import benchmarks, recorder


def main(start: date, end: date, dry_run: bool) -> int:
    print(f"Fetching {benchmarks.DEFAULT_BENCHMARKS} bars from {start} to {end}...")
    series = benchmarks.get_closes_in_range(benchmarks.DEFAULT_BENCHMARKS, start, end)
    if not series:
        print("No bars returned. Check Alpaca data access and date range.", file=sys.stderr)
        return 1

    trading_days = sorted(series.keys())
    print(f"Got {len(trading_days)} trading days: {trading_days[0]} -> {trading_days[-1]}")

    if dry_run:
        for d in trading_days:
            print(f"  {d}: {series[d]}")
        return 0

    written = 0
    for d in trading_days:
        rows = recorder.record_benchmarks(date=d.isoformat(), closes=series[d])
        written += rows
    print(f"Wrote {written} rows to {recorder.BENCHMARKS_CSV}")
    return 0


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=_parse_date, default=benchmarks.BACKFILL_START)
    parser.add_argument("--end", type=_parse_date, default=date.today() - timedelta(days=1))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args.start, args.end, args.dry_run))
