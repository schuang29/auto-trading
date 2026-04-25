"""
Tests for the market-open execution flow. Uses --dry-run mode so no real
orders are placed. Requires valid ALPACA_API_KEY/SECRET in .env to connect
to the paper account for account state reads.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PROPOSALS_DIR = ROOT / "memory" / "proposals"
DECISIONS_DIR = ROOT / "memory" / "decisions"


def write_proposals(data: dict) -> Path:
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = PROPOSALS_DIR / f"{today}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def run_market_open(extra_args: list[str] | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    cmd = [str(PYTHON), str(ROOT / "scripts" / "market_open.py")] + (extra_args or [])
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env=run_env)


class TestMarketOpenDryRun:
    def test_aborts_when_no_proposals_file(self, tmp_path):
        today = date.today().isoformat()
        path = PROPOSALS_DIR / f"{today}.json"
        existed = path.exists()
        backup = path.read_text() if existed else None
        if existed:
            path.unlink()

        result = run_market_open(["--dry-run"])

        if backup:
            path.write_text(backup)

        assert result.returncode == 1
        assert "No proposals file" in result.stdout or "No proposals file" in result.stderr

    def test_skips_when_regime_not_confirmed(self):
        write_proposals({
            "date": date.today().isoformat(),
            "regime": "RISK-ON",
            "confirmed": False,
            "proposals": [{"ticker": "VTI", "side": "buy", "notional": 15000, "rule": "3.1"}],
        })
        result = run_market_open(["--dry-run"])
        assert result.returncode == 0
        assert "not confirmed" in result.stdout.lower()

    def test_skips_when_observe_only(self):
        write_proposals({
            "date": date.today().isoformat(),
            "regime": "RISK-ON",
            "confirmed": True,
            "observe_only": True,
            "proposals": [{"ticker": "VTI", "side": "buy", "notional": 15000, "rule": "3.1"}],
        })
        result = run_market_open(["--dry-run"])
        assert result.returncode == 0
        assert "observe-only" in result.stdout.lower()

    def test_dry_run_approved_order_logs_decision(self):
        write_proposals({
            "date": date.today().isoformat(),
            "regime": "RISK-ON",
            "confirmed": True,
            "proposals": [{"ticker": "VTI", "side": "buy", "notional": 500, "rule": "3.1, 2", "priority": 1}],
        })
        before = set(DECISIONS_DIR.glob("*.md")) if DECISIONS_DIR.exists() else set()

        result = run_market_open(["--dry-run"], env={"_CHECKER_NOW_ET": "2026-04-25T10:00:00"})

        after = set(DECISIONS_DIR.glob("*.md")) if DECISIONS_DIR.exists() else set()
        new_files = after - before

        assert result.returncode == 0
        assert "dry-run" in result.stdout.lower()
        assert len(new_files) == 1, f"Expected 1 new decision file, got {len(new_files)}"

    def test_guardrail_blocks_non_universe_ticker(self):
        write_proposals({
            "date": date.today().isoformat(),
            "regime": "RISK-ON",
            "confirmed": True,
            "proposals": [{"ticker": "AAPL", "side": "buy", "notional": 500, "rule": "3.1"}],
        })
        result = run_market_open(["--dry-run"])
        assert result.returncode == 0
        assert "BLOCKED" in result.stdout

    def test_guardrail_blocks_below_min_notional(self):
        write_proposals({
            "date": date.today().isoformat(),
            "regime": "RISK-ON",
            "confirmed": True,
            "proposals": [{"ticker": "VTI", "side": "buy", "notional": 100, "rule": "3.1"}],
        })
        result = run_market_open(["--dry-run"])
        assert result.returncode == 0
        assert "BLOCKED" in result.stdout
