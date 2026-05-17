# ADR-0008: Dead-man's-switch heartbeat

Date: 2026-05-17
Status: Accepted

## Context

On 2026-05-13→15 the bot went dark for three consecutive trading days
(battery-blocked scheduled tasks — see ADR context in
`memory/health/2026-W20-reliability-incident.md`). Nothing noticed until a
manual review on Sunday 05-17. Every internal failure note the routines wrote
depended on the very push path that was broken, so the failure was invisible
from outside the machine. A trading system whose failure mode is silent
invisibility is more dangerous than one that errors loudly.

The W20 weekly review's #1 proposal was an external watchdog. The notification
channel it assumed (`skills/notifications/`) was never built.

## Decision

**Add `scripts/heartbeat.py`, an independent watchdog run by its own
`AutoTrading-Heartbeat` task at 18:30 ET weekdays (after the 16:15 EOD).** It
verifies, for a *window* of recent trading days (not just today), that each has
a `portfolio_daily.csv` row and a daily log with an `EOD Summary` section, and
that `origin/main..HEAD == 0` (the audit trail actually reached origin). On any
miss it is loud through **three independent channels**: a committed
`memory/health/ALERT-*.md`, an SMTP email (`scripts/notify.py`), and a non-zero
exit (so Task Scheduler also flags it). A daily log carrying an
acknowledged-gap marker (`RELIABILITY GAP` / `NO ROUTINE RAN`) is treated as a
documented outage and does not re-alert.

## Consequences

**Why this design:**

- **Independence.** The heartbeat shares no failure mode with the routines it
  watches — separate task, separate trigger, separate code path. A watchdog
  that dies with the thing it watches is not a watchdog.
- **Windowed, not point.** Checking ~5 calendar days back catches a multi-day
  void even if the heartbeat itself missed runs; old, documented gaps age out.
- **Loud by default, in triplicate.** The guaranteed channels (local file +
  non-zero exit) work with zero configuration; SMTP is the extra reach. The
  notifier never raises, so it cannot mask the underlying alert.
- **Fails safe.** An unknown push state or an internal error escalates to
  ALERT, never to silent OK. A missing holiday in the static 2026 NYSE table
  causes at worst a loud false alarm — the correct failure direction.
- **Acknowledged-gap suppression** ties documentation to silence: a void only
  stops alerting once a human has recorded *why*, which is exactly the
  behavior we want for an audit trail.
- **Testable.** The decision core (`is_trading_day`, `recent_trading_dates`,
  `check_date`, `evaluate`) is pure and parameterized; `tests/test_heartbeat.py`
  covers it without git or network.

**Costs / limits:**

- **Static holiday table** must be refreshed annually (documented in-code).
- **Not real-time.** Detection latency is up to ~26 hours (a Monday failure is
  caught Monday 18:30). Acceptable: the goal is "known within hours, not days,"
  and the routines themselves now also alert on push failure via
  `sync_git.ps1`.
- **SMTP requires operator config** (`SMTP_*`, `NOTIFY_EMAIL_TO` in `.env`).
  Until set, alerts are still durable locally and as exit codes.
- **Not a substitute for the root-cause fix.** The battery-lockout fix
  (ADR-0007 sibling work) is the primary defense; the heartbeat is the net for
  whatever still slips through.

**When to revisit:** if detection latency proves too slow, add an intraday
heartbeat or an external uptime monitor independent of the host entirely.
