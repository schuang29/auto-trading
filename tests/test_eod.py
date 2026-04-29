"""
Tests for scripts/eod.py. Uses mocked Alpaca responses so no live API calls
are needed. Tests the P&L math, trailing stop logic, and file write behaviour.
"""
import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.eod as eod
from skills.alpaca import AccountState


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_account(equity=100_000.0, cash=62_500.0, buying_power=62_500.0) -> AccountState:
    return AccountState(equity=equity, cash=cash, buying_power=buying_power)


def make_position(ticker="VTI", qty=60.0, avg_cost=250.0, current_price=255.0,
                  market_value=15_300.0, unrealized_pl=300.0) -> dict:
    return {
        "ticker": ticker,
        "qty": qty,
        "avg_cost": avg_cost,
        "current_price": current_price,
        "market_value": market_value,
        "unrealized_pl": unrealized_pl,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestEodDryRun:
    def test_empty_portfolio_produces_zero_pl(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eod, "HWM_FILE", tmp_path / "hwm.json")
        monkeypatch.setattr(eod, "POSITIONS_FILE", tmp_path / "positions.md")
        monkeypatch.setattr(eod, "PORTFOLIO_CSV", tmp_path / "portfolio_daily.csv")
        monkeypatch.setattr(eod, "POSITIONS_CSV", tmp_path / "positions_daily.csv")
        monkeypatch.setattr(eod, "BENCHMARKS_CSV", tmp_path / "benchmarks_daily.csv")

        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[]):
            result = eod.main(dry_run=True)

        assert result["totals"]["total_unrealized_pl"] == 0.0
        assert result["totals"]["position_count"] == 0
        assert result["trailing_stop_alerts"] == []

    def test_position_with_gain_no_stop(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eod, "HWM_FILE", tmp_path / "hwm.json")
        monkeypatch.setattr(eod, "POSITIONS_FILE", tmp_path / "positions.md")
        monkeypatch.setattr(eod, "PORTFOLIO_CSV", tmp_path / "portfolio_daily.csv")
        monkeypatch.setattr(eod, "POSITIONS_CSV", tmp_path / "positions_daily.csv")
        monkeypatch.setattr(eod, "BENCHMARKS_CSV", tmp_path / "benchmarks_daily.csv")

        pos = make_position(current_price=255.0, avg_cost=250.0, unrealized_pl=300.0)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = eod.main(dry_run=True)

        assert result["totals"]["total_unrealized_pl"] == 300.0
        assert result["trailing_stop_alerts"] == []
        assert result["positions"][0]["stop_triggered"] is False

    def test_trailing_stop_triggers_at_15pct_drawdown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eod, "HWM_FILE", tmp_path / "hwm.json")
        monkeypatch.setattr(eod, "POSITIONS_FILE", tmp_path / "positions.md")
        monkeypatch.setattr(eod, "PORTFOLIO_CSV", tmp_path / "portfolio_daily.csv")
        monkeypatch.setattr(eod, "POSITIONS_CSV", tmp_path / "positions_daily.csv")
        monkeypatch.setattr(eod, "BENCHMARKS_CSV", tmp_path / "benchmarks_daily.csv")

        # Pre-seed HWM at 100 so current price of 84 = -16% drawdown
        hwm_data = {"VTI": {"hwm": 100.0, "hwm_date": "2026-04-20", "entry_date": "2026-04-20"}}
        (tmp_path / "hwm.json").write_text(json.dumps(hwm_data), encoding="utf-8")

        pos = make_position(current_price=84.0, avg_cost=90.0, market_value=8_400.0, unrealized_pl=-600.0)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = eod.main(dry_run=True)

        assert len(result["trailing_stop_alerts"]) == 1
        assert result["trailing_stop_alerts"][0]["ticker"] == "VTI"
        assert result["positions"][0]["stop_triggered"] is True

    def test_trailing_stop_does_not_trigger_at_14pct_drawdown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eod, "HWM_FILE", tmp_path / "hwm.json")
        monkeypatch.setattr(eod, "POSITIONS_FILE", tmp_path / "positions.md")
        monkeypatch.setattr(eod, "PORTFOLIO_CSV", tmp_path / "portfolio_daily.csv")
        monkeypatch.setattr(eod, "POSITIONS_CSV", tmp_path / "positions_daily.csv")
        monkeypatch.setattr(eod, "BENCHMARKS_CSV", tmp_path / "benchmarks_daily.csv")

        hwm_data = {"VTI": {"hwm": 100.0, "hwm_date": "2026-04-20", "entry_date": "2026-04-20"}}
        (tmp_path / "hwm.json").write_text(json.dumps(hwm_data), encoding="utf-8")

        pos = make_position(current_price=86.0, avg_cost=90.0, market_value=8_600.0, unrealized_pl=-400.0)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = eod.main(dry_run=True)

        assert result["trailing_stop_alerts"] == []
        assert result["positions"][0]["stop_triggered"] is False

    def test_hwm_updates_on_new_high(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eod, "HWM_FILE", tmp_path / "hwm.json")
        monkeypatch.setattr(eod, "POSITIONS_FILE", tmp_path / "positions.md")
        monkeypatch.setattr(eod, "PORTFOLIO_CSV", tmp_path / "portfolio_daily.csv")
        monkeypatch.setattr(eod, "POSITIONS_CSV", tmp_path / "positions_daily.csv")
        monkeypatch.setattr(eod, "BENCHMARKS_CSV", tmp_path / "benchmarks_daily.csv")

        hwm_data = {"VTI": {"hwm": 250.0, "hwm_date": "2026-04-27", "entry_date": "2026-04-27"}}
        (tmp_path / "hwm.json").write_text(json.dumps(hwm_data), encoding="utf-8")

        # Current price 260 > old HWM 250 — should update
        pos = make_position(current_price=260.0, avg_cost=250.0, market_value=15_600.0, unrealized_pl=600.0)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]), \
             patch(
                 "skills.timeseries.benchmarks.get_closes_for_date",
                 return_value={"SPY": 600.0, "AGG": 100.0, "VT": 110.0},
             ):
            result = eod.main(dry_run=False)  # write=True to check file update

        saved = json.loads((tmp_path / "hwm.json").read_text(encoding="utf-8"))
        assert saved["VTI"]["hwm"] == 260.0
        assert result["positions"][0]["hwm"] == 260.0

    def test_dry_run_does_not_write_files(self, tmp_path, monkeypatch):
        hwm_path = tmp_path / "hwm.json"
        pos_path = tmp_path / "positions.md"
        monkeypatch.setattr(eod, "HWM_FILE", hwm_path)
        monkeypatch.setattr(eod, "POSITIONS_FILE", pos_path)

        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[]):
            eod.main(dry_run=True)

        assert not hwm_path.exists(), "dry-run should not write hwm file"
        assert not pos_path.exists(), "dry-run should not write positions.md"
