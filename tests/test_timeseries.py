"""
Tests for skills.timeseries.recorder. Covers idempotence, math correctness,
schema, and 60/40 blend math. No Alpaca calls — paths are redirected to tmp.
"""
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.timeseries import recorder


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ── Portfolio ─────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_writes_first_row_with_starting_equity_baseline(self, tmp_path):
        path = tmp_path / "portfolio_daily.csv"
        recorder.record_portfolio(
            date="2026-04-25", equity=99_500.0, cash=70_000.0,
            positions_value=29_500.0, starting_equity=100_000.0, path=path,
        )
        rows = _read_csv(path)
        assert len(rows) == 1
        r = rows[0]
        assert r["date"] == "2026-04-25"
        assert float(r["equity"]) == 99_500.0
        assert float(r["daily_pnl"]) == -500.0
        assert float(r["daily_pnl_pct"]) == pytest.approx(-0.005, rel=1e-6)
        assert float(r["cumulative_pnl"]) == -500.0
        assert float(r["cumulative_pnl_pct"]) == pytest.approx(-0.005, rel=1e-6)

    def test_idempotent_same_day_overwrites_no_duplicate(self, tmp_path):
        path = tmp_path / "portfolio_daily.csv"
        recorder.record_portfolio(
            date="2026-04-25", equity=99_500.0, cash=70_000.0,
            positions_value=29_500.0, starting_equity=100_000.0, path=path,
        )
        recorder.record_portfolio(
            date="2026-04-25", equity=99_750.0, cash=69_750.0,
            positions_value=30_000.0, starting_equity=100_000.0, path=path,
        )
        rows = _read_csv(path)
        assert len(rows) == 1
        assert float(rows[0]["equity"]) == 99_750.0

    def test_daily_pnl_uses_prior_day_equity(self, tmp_path):
        path = tmp_path / "portfolio_daily.csv"
        recorder.record_portfolio(
            date="2026-04-25", equity=99_500.0, cash=70_000.0,
            positions_value=29_500.0, starting_equity=100_000.0, path=path,
        )
        recorder.record_portfolio(
            date="2026-04-26", equity=100_500.0, cash=68_000.0,
            positions_value=32_500.0, starting_equity=100_000.0, path=path,
        )
        rows = _read_csv(path)
        assert len(rows) == 2
        day2 = rows[1]
        assert float(day2["daily_pnl"]) == 1_000.0
        assert float(day2["daily_pnl_pct"]) == pytest.approx(1_000.0 / 99_500.0, rel=1e-6)
        assert float(day2["cumulative_pnl"]) == 500.0
        assert float(day2["cumulative_pnl_pct"]) == pytest.approx(0.005, rel=1e-6)

    def test_schema_matches_plan(self, tmp_path):
        path = tmp_path / "portfolio_daily.csv"
        recorder.record_portfolio(
            date="2026-04-25", equity=99_500.0, cash=70_000.0,
            positions_value=29_500.0, starting_equity=100_000.0, path=path,
        )
        with path.open("r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        assert header == recorder.PORTFOLIO_FIELDS


# ── Positions ─────────────────────────────────────────────────────────────────

class TestPositions:
    def _pos(self, **overrides) -> dict:
        base = {
            "ticker": "VTI", "qty": 60.0, "avg_cost": 250.0,
            "current_price": 255.0, "market_value": 15_300.0, "unrealized_pl": 300.0,
        }
        base.update(overrides)
        return base

    def test_writes_one_row_per_position(self, tmp_path):
        path = tmp_path / "positions_daily.csv"
        positions = [self._pos(), self._pos(ticker="QQQ", market_value=8_000.0)]
        n = recorder.record_positions(
            date="2026-04-25", positions=positions,
            portfolio_equity=100_000.0, path=path,
        )
        assert n == 2
        rows = _read_csv(path)
        assert {r["ticker"] for r in rows} == {"VTI", "QQQ"}

    def test_weight_pct_is_decimal_ratio(self, tmp_path):
        path = tmp_path / "positions_daily.csv"
        recorder.record_positions(
            date="2026-04-25",
            positions=[self._pos(market_value=25_000.0)],
            portfolio_equity=100_000.0, path=path,
        )
        rows = _read_csv(path)
        assert float(rows[0]["weight_pct"]) == pytest.approx(0.25, rel=1e-9)

    def test_idempotent_replaces_dates_position_set(self, tmp_path):
        path = tmp_path / "positions_daily.csv"
        recorder.record_positions(
            date="2026-04-25",
            positions=[self._pos(), self._pos(ticker="QQQ")],
            portfolio_equity=100_000.0, path=path,
        )
        recorder.record_positions(
            date="2026-04-25",
            positions=[self._pos()],  # QQQ closed out
            portfolio_equity=100_000.0, path=path,
        )
        rows = _read_csv(path)
        assert len(rows) == 1
        assert rows[0]["ticker"] == "VTI"

    def test_does_not_disturb_other_dates(self, tmp_path):
        path = tmp_path / "positions_daily.csv"
        recorder.record_positions(
            date="2026-04-24", positions=[self._pos()],
            portfolio_equity=100_000.0, path=path,
        )
        recorder.record_positions(
            date="2026-04-25", positions=[self._pos(ticker="QQQ")],
            portfolio_equity=100_000.0, path=path,
        )
        # Re-record day 2 — day 1 must remain intact.
        recorder.record_positions(
            date="2026-04-25", positions=[self._pos(ticker="QQQ"), self._pos(ticker="BND")],
            portfolio_equity=100_000.0, path=path,
        )
        rows = _read_csv(path)
        d24 = [r for r in rows if r["date"] == "2026-04-24"]
        d25 = [r for r in rows if r["date"] == "2026-04-25"]
        assert len(d24) == 1 and d24[0]["ticker"] == "VTI"
        assert {r["ticker"] for r in d25} == {"QQQ", "BND"}

    def test_schema_matches_plan(self, tmp_path):
        path = tmp_path / "positions_daily.csv"
        recorder.record_positions(
            date="2026-04-25", positions=[self._pos()],
            portfolio_equity=100_000.0, path=path,
        )
        with path.open("r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        assert header == recorder.POSITIONS_FIELDS


# ── Benchmarks + 60/40 blend ──────────────────────────────────────────────────

class TestBenchmarks:
    def test_first_row_has_zero_returns(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19",
            closes={"SPY": 600.0, "AGG": 100.0, "VT": 110.0},
            path=path,
        )
        rows = _read_csv(path)
        for r in rows:
            assert float(r["daily_return_pct"]) == 0.0
            assert float(r["cumulative_return_pct"]) == 0.0

    def test_blend_row_emitted_when_spy_and_agg_present(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19",
            closes={"SPY": 600.0, "AGG": 100.0},
            path=path,
        )
        rows = _read_csv(path)
        bms = {r["benchmark"] for r in rows}
        assert "60_40_BLEND" in bms
        blend = next(r for r in rows if r["benchmark"] == "60_40_BLEND")
        assert blend["close_price"] == ""

    def test_blend_skipped_without_both_spy_and_agg(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19", closes={"VT": 110.0}, path=path,
        )
        rows = _read_csv(path)
        assert {r["benchmark"] for r in rows} == {"VT"}

    def test_daily_return_computed_from_prior_close(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19", closes={"SPY": 600.0}, path=path,
        )
        recorder.record_benchmarks(
            date="2026-04-20", closes={"SPY": 606.0}, path=path,
        )
        rows = sorted(_read_csv(path), key=lambda r: r["date"])
        assert float(rows[1]["daily_return_pct"]) == pytest.approx(0.01, rel=1e-6)
        assert float(rows[1]["cumulative_return_pct"]) == pytest.approx(0.01, rel=1e-6)

    def test_blend_math_matches_60_40_daily_rebalance(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19",
            closes={"SPY": 600.0, "AGG": 100.0}, path=path,
        )
        recorder.record_benchmarks(
            date="2026-04-20",
            closes={"SPY": 606.0, "AGG": 100.5}, path=path,
        )
        rows = _read_csv(path)
        blend_d2 = next(
            r for r in rows
            if r["benchmark"] == "60_40_BLEND" and r["date"] == "2026-04-20"
        )
        # SPY +1.0%, AGG +0.5% -> blend = 0.6*0.01 + 0.4*0.005 = 0.008
        assert float(blend_d2["daily_return_pct"]) == pytest.approx(0.008, rel=1e-9)
        assert float(blend_d2["cumulative_return_pct"]) == pytest.approx(0.008, rel=1e-9)

    def test_idempotent_replaces_existing_date(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19", closes={"SPY": 600.0, "AGG": 100.0}, path=path,
        )
        recorder.record_benchmarks(
            date="2026-04-19", closes={"SPY": 605.0, "AGG": 101.0}, path=path,
        )
        rows = _read_csv(path)
        spy = [r for r in rows if r["benchmark"] == "SPY"]
        assert len(spy) == 1
        assert float(spy[0]["close_price"]) == 605.0

    def test_recompute_runs_across_full_series_on_each_write(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19", closes={"SPY": 600.0, "AGG": 100.0}, path=path,
        )
        recorder.record_benchmarks(
            date="2026-04-21", closes={"SPY": 612.0, "AGG": 101.0}, path=path,
        )
        # Insert a day in between -> day 3's daily return should now reference day 2.
        recorder.record_benchmarks(
            date="2026-04-20", closes={"SPY": 606.0, "AGG": 100.5}, path=path,
        )
        rows = sorted(
            (r for r in _read_csv(path) if r["benchmark"] == "SPY"),
            key=lambda r: r["date"],
        )
        # Day 3 daily = 612/606 - 1
        assert float(rows[2]["daily_return_pct"]) == pytest.approx(612.0 / 606.0 - 1, rel=1e-6)
        # Cumulative from start = 612/600 - 1 = 0.02
        assert float(rows[2]["cumulative_return_pct"]) == pytest.approx(0.02, rel=1e-6)

    def test_schema_matches_plan(self, tmp_path):
        path = tmp_path / "benchmarks_daily.csv"
        recorder.record_benchmarks(
            date="2026-04-19", closes={"SPY": 600.0}, path=path,
        )
        with path.open("r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        assert header == recorder.BENCHMARKS_FIELDS
