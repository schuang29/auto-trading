"""
Tests for the dead-man's-switch (scripts/heartbeat.py).

Covers the pure decision core: trading-day calendar, the recent-window
selection, per-day audit checks, acknowledged-gap suppression, and the
push-state escalation. No git or network — `unpushed` is injected.
"""
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import heartbeat  # noqa: E402


# ── Calendar ──────────────────────────────────────────────────────────────────

class TestIsTradingDay:
    def test_normal_weekday_is_trading(self):
        assert heartbeat.is_trading_day(date(2026, 5, 12))  # a Tuesday

    @pytest.mark.parametrize("d", [date(2026, 5, 16), date(2026, 5, 17)])
    def test_weekend_is_not_trading(self, d):
        assert not heartbeat.is_trading_day(d)

    @pytest.mark.parametrize("d", [
        date(2026, 1, 1),    # New Year's
        date(2026, 5, 25),   # Memorial Day
        date(2026, 7, 3),    # Independence (observed)
        date(2026, 12, 25),  # Christmas
    ])
    def test_known_holiday_is_not_trading(self, d):
        assert not heartbeat.is_trading_day(d)


class TestRecentTradingDates:
    def test_includes_today_when_trading_day(self):
        # Friday 2026-05-15
        now = datetime(2026, 5, 15, 18, 30)
        dates = heartbeat.recent_trading_dates(now)
        assert date(2026, 5, 15) in dates

    def test_excludes_weekend_days_in_window(self):
        # Monday 2026-05-18 — window reaches back over the 16/17 weekend.
        now = datetime(2026, 5, 18, 18, 30)
        dates = heartbeat.recent_trading_dates(now)
        assert date(2026, 5, 16) not in dates
        assert date(2026, 5, 17) not in dates
        assert date(2026, 5, 15) in dates  # prior trading day still caught

    def test_excludes_holiday_in_window(self):
        # Tuesday after Memorial Day (Mon 2026-05-25 is a holiday).
        now = datetime(2026, 5, 26, 18, 30)
        dates = heartbeat.recent_trading_dates(now)
        assert date(2026, 5, 25) not in dates

    def test_empty_window_returns_skip_input(self):
        # Saturday with a zero-day lookback -> nothing to assert.
        now = datetime(2026, 5, 16, 18, 30)
        assert heartbeat.recent_trading_dates(now, lookback_days=0) == []


# ── Per-day audit check ───────────────────────────────────────────────────────

def _seed(root: Path, *, csv_dates=(), daily=None):
    """daily: dict {date_iso: file_text}."""
    ts = root / "memory" / "timeseries"
    ts.mkdir(parents=True, exist_ok=True)
    lines = ["date,equity,cash,positions_value,daily_pnl,daily_pnl_pct,"
             "cumulative_pnl,cumulative_pnl_pct"]
    for d in csv_dates:
        lines.append(f"{d},100000,5000,95000,0,0,0,0")
    (ts / "portfolio_daily.csv").write_text("\n".join(lines) + "\n",
                                            encoding="utf-8")
    dd = root / "memory" / "daily"
    dd.mkdir(parents=True, exist_ok=True)
    for iso, text in (daily or {}).items():
        (dd / f"{iso}.md").write_text(text, encoding="utf-8")


class TestCheckDate:
    def test_healthy_day_returns_none(self, tmp_path):
        d = date(2026, 5, 12)
        _seed(tmp_path, csv_dates=["2026-05-12"],
              daily={"2026-05-12": "# Daily\n## EOD Summary\nall good"})
        assert heartbeat.check_date(tmp_path, d) is None

    def test_missing_csv_row_flags(self, tmp_path):
        d = date(2026, 5, 12)
        _seed(tmp_path, csv_dates=[],
              daily={"2026-05-12": "## EOD Summary\nx"})
        reason = heartbeat.check_date(tmp_path, d)
        assert reason and "no portfolio_daily.csv row" in reason

    def test_missing_daily_file_flags(self, tmp_path):
        d = date(2026, 5, 12)
        _seed(tmp_path, csv_dates=["2026-05-12"], daily={})
        reason = heartbeat.check_date(tmp_path, d)
        assert reason and "no daily log file" in reason

    def test_daily_without_eod_section_flags(self, tmp_path):
        d = date(2026, 5, 12)
        _seed(tmp_path, csv_dates=["2026-05-12"],
              daily={"2026-05-12": "# Daily\n## Midday Check\nonly midday"})
        reason = heartbeat.check_date(tmp_path, d)
        assert reason and "no EOD Summary section" in reason

    def test_acknowledged_gap_marker_suppresses_alert(self, tmp_path):
        # No csv row, no EOD — but the day is documented as a known outage.
        d = date(2026, 5, 13)
        _seed(tmp_path, csv_dates=[],
              daily={"2026-05-13": "# Daily Log — 2026-05-13\n"
                                   "RELIABILITY GAP — NO ROUTINE RAN"})
        assert heartbeat.check_date(tmp_path, d) is None


# ── Evaluate (decision core) ──────────────────────────────────────────────────

class TestEvaluate:
    def _seed_all_healthy(self, tmp_path, now):
        dates = heartbeat.recent_trading_dates(now)
        _seed(
            tmp_path,
            csv_dates=[d.isoformat() for d in dates],
            daily={d.isoformat(): "## EOD Summary\nok" for d in dates},
        )
        return dates

    def test_ok_when_everything_present_and_pushed(self, tmp_path):
        now = datetime(2026, 5, 15, 18, 30)
        dates = self._seed_all_healthy(tmp_path, now)
        status, reasons, checked = heartbeat.evaluate(now, tmp_path, unpushed=0)
        assert status == "ok"
        assert reasons == []
        assert checked == dates

    def test_alert_when_a_day_is_missing(self, tmp_path):
        now = datetime(2026, 5, 15, 18, 30)
        self._seed_all_healthy(tmp_path, now)
        # Wipe one day's daily log to simulate a dark day.
        miss = heartbeat.recent_trading_dates(now)[-1]
        (tmp_path / "memory" / "daily" / f"{miss.isoformat()}.md").unlink()
        status, reasons, _ = heartbeat.evaluate(now, tmp_path, unpushed=0)
        assert status == "alert"
        assert any(miss.isoformat() in r for r in reasons)

    def test_alert_when_audit_trail_not_pushed(self, tmp_path):
        now = datetime(2026, 5, 15, 18, 30)
        self._seed_all_healthy(tmp_path, now)
        status, reasons, _ = heartbeat.evaluate(now, tmp_path, unpushed=3)
        assert status == "alert"
        assert any("NOT pushed" in r and "3" in r for r in reasons)

    def test_alert_when_push_state_unknown(self, tmp_path):
        now = datetime(2026, 5, 15, 18, 30)
        self._seed_all_healthy(tmp_path, now)
        status, reasons, _ = heartbeat.evaluate(now, tmp_path, unpushed=None)
        assert status == "alert"
        assert any("could not verify origin/main" in r for r in reasons)

    def test_skip_when_no_trading_days(self, tmp_path, monkeypatch):
        # Force an empty window to exercise the skip branch.
        monkeypatch.setattr(heartbeat, "recent_trading_dates",
                            lambda now: [])
        now = datetime(2026, 5, 16, 18, 30)
        status, reasons, checked = heartbeat.evaluate(now, tmp_path, unpushed=0)
        assert status == "skip"
        assert reasons == [] and checked == []
