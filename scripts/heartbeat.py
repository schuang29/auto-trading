"""
Dead-man's-switch for the trading bot.

WHY THIS EXISTS: on 2026-05-13→15 the bot went dark for three consecutive
trading days (battery-blocked scheduled tasks) and NOTHING noticed until a
manual review on Sunday 05-17. A trading system whose failure mode is silent
invisibility is more dangerous than one that errors loudly. This script is the
external watchdog: it runs after EOD and asserts that the day's audit trail
actually exists AND reached origin. On any miss it is LOUD — a committed
ALERT file, an SMTP email, and a non-zero exit (so Task Scheduler also flags
it). It must NEVER fail silently: even an internal error writes an alert.

It checks a small WINDOW of recent trading days, not just today, so a void is
still caught even if the heartbeat itself missed a run. A trading day that has
an acknowledged gap marker in its daily log (see scripts that document known
outages) is treated as resolved and does not re-alert forever.

Design for testability: the decision logic (`is_trading_day`,
`recent_trading_dates`, `evaluate`) is pure and parameterized; only `main`
touches the network/filesystem side effects.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# NYSE holidays for 2026. MUST be refreshed annually. A holiday MISSING from
# this set causes at worst a loud false alert — the safe failure direction for
# a dead-man's-switch. A non-trading day wrongly treated as trading is far less
# dangerous than a real dark day going unnoticed.
NYSE_HOLIDAYS = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King Jr. Day
    date(2026, 2, 16),   # Washington's Birthday
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed — Jul 4 is a Saturday)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving Day
    date(2026, 12, 25),  # Christmas Day
}

# Substrings that mark a daily log as an ACKNOWLEDGED outage. If a trading
# day's daily log contains any of these, the heartbeat treats that day as
# resolved (the gap is documented on purpose) and does not alert on it.
ACK_GAP_MARKERS = ("RELIABILITY GAP", "NO ROUTINE RAN", "ACKNOWLEDGED GAP")

# How many calendar days back to scan. ~5 calendar days covers a full trading
# week so a multi-day void is caught even if the heartbeat missed its own runs,
# while old, already-documented gaps naturally age out of the window.
LOOKBACK_DAYS = 5


def is_trading_day(d: date) -> bool:
    """True if `d` is a weekday and not a known NYSE holiday."""
    if d.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    return d not in NYSE_HOLIDAYS


def recent_trading_dates(now: datetime, lookback_days: int = LOOKBACK_DAYS) -> list[date]:
    """Trading days in [now-lookback, today].

    The heartbeat is scheduled well after the EOD routine, so if today is a
    trading day its EOD is already due and today is included. Returns [] only
    when the whole window has no trading days (effectively never for a 5-day
    window, but kept explicit).
    """
    today = now.date()
    out = [
        today - timedelta(days=i)
        for i in range(lookback_days + 1)
    ]
    return sorted(d for d in out if is_trading_day(d))


def _portfolio_dates(root: Path) -> set[str]:
    csv_path = root / "memory" / "timeseries" / "portfolio_daily.csv"
    if not csv_path.exists():
        return set()
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return {row["date"] for row in csv.DictReader(f) if row.get("date")}


def _daily_text(root: Path, d: date) -> str | None:
    p = root / "memory" / "daily" / f"{d.isoformat()}.md"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def check_date(root: Path, d: date) -> str | None:
    """Return a failure reason for trading day `d`, or None if it is healthy
    or has an acknowledged-gap marker."""
    iso = d.isoformat()
    text = _daily_text(root, d)

    if text is not None and any(m in text for m in ACK_GAP_MARKERS):
        return None  # documented outage — do not re-alert

    problems = []
    if iso not in _portfolio_dates(root):
        problems.append("no portfolio_daily.csv row")
    if text is None:
        problems.append("no daily log file")
    elif "EOD Summary" not in text:
        problems.append("daily log has no EOD Summary section")

    if problems:
        return f"{iso}: " + "; ".join(problems)
    return None


def unpushed_count(root: Path) -> int | None:
    """Commits on HEAD not on origin/main. None if it cannot be determined
    (git/network unavailable) — that is logged, not alerted on by itself."""
    try:
        subprocess.run(
            ["git", "fetch", "origin", "main", "--quiet"],
            cwd=root, timeout=60, capture_output=True,
        )
        res = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            cwd=root, timeout=30, capture_output=True, text=True,
        )
        if res.returncode != 0:
            return None
        return int(res.stdout.strip())
    except Exception:  # noqa: BLE001 — never crash the watchdog
        return None


def evaluate(
    now: datetime, root: Path, unpushed: int | None
) -> tuple[str, list[str], list[date]]:
    """Pure decision core.

    Returns (status, reasons, dates_checked) where status is:
      'ok'    — everything verified
      'alert' — one or more problems (reasons non-empty)
      'skip'  — nothing to assert (non-trading day)
    """
    dates = recent_trading_dates(now)
    if not dates:
        return "skip", [], []

    reasons = [r for d in dates if (r := check_date(root, d)) is not None]

    if unpushed is None:
        reasons.append(
            "could not verify origin/main sync (git/network unavailable)"
        )
    elif unpushed > 0:
        reasons.append(
            f"audit trail NOT pushed: {unpushed} local commit(s) "
            f"not on origin/main"
        )

    return ("alert" if reasons else "ok"), reasons, dates


# ── Side-effecting glue (not unit-tested; exercised via the wrapper) ──────────

def _append_log(root: Path, line: str) -> None:
    health = root / "memory" / "health"
    health.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (health / "heartbeat.log").open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")


def _write_alert(root: Path, reasons: list[str], dates: list[date]) -> Path:
    health = root / "memory" / "health"
    health.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = health / f"ALERT-{now.strftime('%Y-%m-%d-%H%M%S')}.md"
    body = (
        f"# HEARTBEAT ALERT\n\n"
        f"**Raised:** {now.strftime('%Y-%m-%d %H:%M:%S')} (local)\n"
        f"**Trading days checked:** "
        f"{', '.join(d.isoformat() for d in dates) or '(none)'}\n\n"
        f"## Problems\n\n"
        + "".join(f"- {r}\n" for r in reasons)
        + "\n## What this means\n\n"
        "A routine did not produce its expected audit output, or the audit "
        "trail did not reach origin. The bot may have gone dark. Investigate "
        "now — do not assume it is benign.\n\n"
        "## First checks\n\n"
        "1. Are the AutoTrading-* scheduled tasks enabled and battery-safe "
        "(`DisallowStartIfOnBatteries=False`)?\n"
        "2. Is `GITHUB_TOKEN` set in `.env` (headless push)?\n"
        "3. Read the most recent `memory/daily/*.md` and the routine `logs/`.\n"
        "4. If a day legitimately had no run, add an acknowledged-gap marker "
        f"({' / '.join(ACK_GAP_MARKERS)}) to its daily log so this stops "
        "re-alerting.\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def _notify(subject: str, body: str) -> None:
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "notify.py"),
             "--subject", subject, "--body", body],
            timeout=60, capture_output=True,
        )
    except Exception:  # noqa: BLE001 — local alert + exit code are guaranteed
        pass


def _commit_and_push(root: Path, alert_path: Path) -> None:
    """Best-effort: get the ALERT into the audit trail and onto origin. The
    local file + SMTP + non-zero exit are the guaranteed channels, so failures
    here are swallowed."""
    try:
        subprocess.run(["git", "add", str(alert_path)], cwd=root,
                        timeout=30, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m",
             f"health: heartbeat ALERT {datetime.now():%Y-%m-%d}"],
            cwd=root, timeout=30, capture_output=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=root,
                        timeout=120, capture_output=True)
    except Exception:  # noqa: BLE001
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Trading-bot dead-man's-switch.")
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--now", default=None,
                   help="ISO datetime override for testing.")
    args = p.parse_args(argv)
    root = Path(args.root)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now()

    try:
        status, reasons, dates = evaluate(now, root, unpushed_count(root))
    except Exception as exc:  # noqa: BLE001 — a watchdog must not die quietly
        reasons = [f"heartbeat internal error: {exc!r}"]
        status, dates = "alert", []

    if status == "skip":
        _append_log(root, "SKIP non-trading day")
        return 0
    if status == "ok":
        _append_log(root,
                    f"OK {', '.join(d.isoformat() for d in dates)}")
        return 0

    # status == "alert"
    summary = " | ".join(reasons)
    _append_log(root, f"ALERT {summary}")
    alert_path = _write_alert(root, reasons, dates)
    _notify(f"HEARTBEAT ALERT {now:%Y-%m-%d}",
            alert_path.read_text(encoding='utf-8'))
    _commit_and_push(root, alert_path)
    sys.stderr.write(f"HEARTBEAT ALERT: {summary}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
