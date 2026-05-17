# Reliability Incident — W20 (2026-05-12 → 2026-05-17)

**Status:** root-caused and remediated in code 2026-05-17. Three operator
actions remain (see "Outstanding — requires the user").

---

## What happened

| Date | What ran |
|---|---|
| 2026-05-11 (Mon) | Full, clean run (pre-market, midday, EOD). |
| 2026-05-12 (Tue) | Ran, but DEGRADED: pre-market wrote literal `@-` (no regime signal); all three git pushes failed (`wincredman`). |
| 2026-05-13 (Wed) | **Nothing ran.** |
| 2026-05-14 (Thu) | **Nothing ran.** |
| 2026-05-15 (Fri) | **Nothing ran**, including the Friday weekly review. |
| 2026-05-17 (Sun) | Off-schedule catch-up run; W20 weekly produced late; the dark days surfaced for the first time. |

Only 1 of 5 trading days (05-11) ran cleanly. The void was silent for ~4 days.

## Root causes (two independent failures)

1. **Battery lockout (the 3-day void).** `scripts/setup_scheduler.ps1` built
   task settings with only `-StartWhenAvailable -WakeToRun`.
   `New-ScheduledTaskSettingsSet` defaults `DisallowStartIfOnBatteries=$true`
   **and** `StopIfGoingOnBatteries=$true`. The laptop was on battery at the
   scheduled times 05-13→15, so all five tasks silently declined to start.
   `NumberOfMissedRuns` stayed 0 (Windows does not count battery-blocked
   starts), so the scheduler looked healthy while the bot was dark.

2. **Headless push failure (audit trail not durable).** `credential.helper`
   was `manager` with no `credentialStore`, defaulting to `wincredman`, which
   cannot operate in the non-interactive scheduled context. Every push from
   05-12 on failed; the failure was only ever written to a *local* note that
   itself never got pushed. By 05-17 the local branch was 10 commits ahead of
   origin.

3. **No watchdog.** Nothing external checked that the bot actually ran. The
   failure mode was silent invisibility — the most dangerous kind.

## Remediation applied 2026-05-17 (in code)

- **Backlog pushed.** All 10 local commits are now on `origin/main`.
- **Battery fix.** `setup_scheduler.ps1` now clears
  `DisallowStartIfOnBatteries` and `StopIfGoingOnBatteries` on the shared
  settings object (there is no negative switch — it must be set on the object).
- **Durable headless credential.** `scripts/git-credential-env.sh` supplies a
  PAT from `$GITHUB_TOKEN` (gitignored `.env`) for `get` only, silent
  otherwise so interactive use falls through to `manager`. Wired into
  `.git/config` as an idempotent, self-healing chain `["" reset, env-token,
  manager]`. The PAT is never written to `.git/config` or committed. See
  ADR-0007.
- **Loud push verification.** New `scripts/sync_git.ps1`, called at the end of
  every wrapper, pushes + verifies `origin/main..HEAD == 0` and, on failure,
  writes a committed `memory/health/PUSH-FAILED-*.md`, emails via
  `scripts/notify.py`, and exits non-zero. No more silent local-only notes.
- **Dead-man's-switch.** New `scripts/heartbeat.py` + `run_heartbeat.ps1` +
  `AutoTrading-Heartbeat` task (18:30 ET weekdays). Verifies a window of recent
  trading days has a `portfolio_daily.csv` row + an EOD section, and that the
  audit trail reached origin. On any miss: committed `ALERT-*.md`, SMTP email,
  non-zero exit. Acknowledged-gap markers suppress re-alerts. See ADR-0008.
- **05-13→15 documented, not fabricated.** `memory/daily/2026-05-13..15.md`
  each carry a `RELIABILITY GAP — NO ROUTINE RAN` marker. No timeseries rows
  were invented (hard rules #5, #6). Verified: `heartbeat.evaluate` now treats
  these three days as acknowledged and the void no longer alerts.
- **Tests.** `tests/test_heartbeat.py`, `tests/test_notify.py` added; full
  suite green (59 passed).

## Outstanding — requires the user

1. **Run `setup_scheduler.ps1` as Administrator once** (before Mon 05-18
   07:30 ET). The live tasks still carry the old battery-lockout setting;
   `Set-ScheduledTask` is access-denied without elevation. This re-registers
   all six tasks (incl. the new `AutoTrading-Heartbeat`) battery-safe.
2. **Create a fine-grained GitHub PAT** (this repo only, Contents: Read and
   write) and put it in `.env` as `GITHUB_TOKEN=...`. Until then the scheduled
   push still cannot authenticate.
3. **Fill in `SMTP_*` + `NOTIFY_EMAIL_TO` in `.env`** for email alerts.
   Until then, alerts still land locally in `memory/health/` and as non-zero
   exits — email is the extra reach.

Cross-reference: `memory/weekly/2026-W20.md` (full analysis),
`docs/decisions/0007-headless-git-credential.md`,
`docs/decisions/0008-dead-mans-switch-heartbeat.md`.
