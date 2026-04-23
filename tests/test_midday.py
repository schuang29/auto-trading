"""
Tests for scripts/midday.py. Uses mocked Alpaca responses — no live API calls.
"""
import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.midday as midday
from skills.alpaca import AccountState


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_account(equity=100_000.0, cash=62_500.0) -> AccountState:
    return AccountState(equity=equity, cash=cash, buying_power=cash)


def make_position(ticker="VTI", qty=60.0, avg_cost=250.0, current_price=255.0,
                  market_value=15_300.0, unrealized_pl=300.0,
                  unrealized_intraday_pl=150.0, unrealized_intraday_plpc=0.01) -> dict:
    return {
        "ticker": ticker,
        "qty": qty,
        "avg_cost": avg_cost,
        "current_price": current_price,
        "market_value": market_value,
        "unrealized_pl": unrealized_pl,
        "unrealized_intraday_pl": unrealized_intraday_pl,
        "unrealized_intraday_plpc": unrealized_intraday_plpc,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestMiddayDryRun:
    def test_empty_portfolio_no_alerts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(midday, "HWM_FILE", tmp_path / "hwm.json")

        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[]):
            result = midday.main(dry_run=True)

        assert result["trailing_stop_alerts"] == []
        assert result["large_movers"] == []
        assert result["positions"] == []

    def test_trailing_stop_triggers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(midday, "HWM_FILE", tmp_path / "hwm.json")

        hwm_data = {"VTI": {"hwm": 100.0, "hwm_date": "2026-04-27", "entry_date": "2026-04-27"}}
        (tmp_path / "hwm.json").write_text(json.dumps(hwm_data), encoding="utf-8")

        pos = make_position(current_price=84.0, unrealized_intraday_plpc=-0.01)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = midday.main(dry_run=True)

        assert len(result["trailing_stop_alerts"]) == 1
        assert result["trailing_stop_alerts"][0]["ticker"] == "VTI"
        assert result["positions"][0]["stop_triggered"] is True

    def test_large_mover_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(midday, "HWM_FILE", tmp_path / "hwm.json")

        # intraday move of +3% — above the 2% threshold
        pos = make_position(unrealized_intraday_plpc=0.03)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = midday.main(dry_run=True)

        assert len(result["large_movers"]) == 1
        assert result["large_movers"][0]["ticker"] == "VTI"

    def test_small_mover_not_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(midday, "HWM_FILE", tmp_path / "hwm.json")

        # intraday move of +1% — below the 2% threshold
        pos = make_position(unrealized_intraday_plpc=0.01)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = midday.main(dry_run=True)

        assert result["large_movers"] == []

    def test_hwm_updated_on_intraday_high(self, tmp_path, monkeypatch):
        monkeypatch.setattr(midday, "HWM_FILE", tmp_path / "hwm.json")

        hwm_data = {"VTI": {"hwm": 250.0, "hwm_date": "2026-04-27", "entry_date": "2026-04-27"}}
        (tmp_path / "hwm.json").write_text(json.dumps(hwm_data), encoding="utf-8")

        pos = make_position(current_price=260.0)
        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[pos]):
            result = midday.main(dry_run=False)

        saved = json.loads((tmp_path / "hwm.json").read_text(encoding="utf-8"))
        assert saved["VTI"]["hwm"] == 260.0
        assert result["positions"][0]["hwm"] == 260.0

    def test_dry_run_does_not_write_hwm(self, tmp_path, monkeypatch):
        hwm_path = tmp_path / "hwm.json"
        monkeypatch.setattr(midday, "HWM_FILE", hwm_path)

        with patch("skills.alpaca.get_account", return_value=make_account()), \
             patch("skills.alpaca.get_positions", return_value=[]):
            midday.main(dry_run=True)

        assert not hwm_path.exists()
