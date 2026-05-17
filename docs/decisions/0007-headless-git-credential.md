# ADR-0007: Headless git credential via PAT-in-.env helper

Date: 2026-05-17
Status: Accepted

## Context

The bot's audit trail (`memory/`) is only durable once it reaches
`origin/main`. The scheduled routines run in a non-interactive Windows Task
Scheduler context. `credential.helper` was `manager` (Git Credential Manager)
with no `credentialStore` set, so it defaulted to `wincredman` (Windows
Credential Manager), which **cannot operate without an interactive desktop
session**. Every push from 2026-05-12 onward failed with
`fatal: Unable to persist credentials with the 'wincredman' credential store`.
The failure was written only to a local note that itself never got pushed; by
2026-05-17 the local branch was 10 commits ahead of origin. See
`memory/health/2026-W20-reliability-incident.md`.

Options considered:

1. **PAT in gitignored `.env`, surfaced by a custom credential helper.**
2. `credential.credentialStore = dpapi` + a one-time interactive seed.
3. Install GitHub CLI and `gh auth setup-git`.

## Decision

**Option 1.** A committed shell helper `scripts/git-credential-env.sh` emits
`username=x-access-token` / `password=$GITHUB_TOKEN` for the `get` operation
only, and only when `GITHUB_TOKEN` is set. The token lives solely in the
gitignored `.env` (loaded into the process environment by every wrapper). The
local credential chain is rebuilt idempotently as
`["" reset, !sh git-credential-env.sh, manager]`, which git evaluates as
`[env-token, manager]`: the token helper runs first in the headless context,
and when no token is present it is silent so interactive use falls through to
`manager`.

## Consequences

**Why this is the right design:**

- **Zero dependence on any OS credential store.** The failure mode that caused
  the incident is structurally removed, not worked around.
- **No secret is committed or persisted in git config.** `.git/config` stores
  only this script's path; the script references `$GITHUB_TOKEN`, never its
  value. `.env` is gitignored (hard rule #1 intact).
- **Interactive use is unchanged.** Without a token the helper is silent and
  `manager` serves cached credentials, exactly as before.
- **Self-healing.** `sync_git.ps1` rebuilds the chain every run, so a clobbered
  `.git/config` recovers automatically.

**Costs / risks:**

- **A long-lived PAT exists.** Mitigated by fine-grained scope (this repo only,
  Contents: R/W) and `.env` being gitignored. Rotation is manual.
- **Requires one operator action:** minting the PAT and pasting it into `.env`.
  Until then the scheduled push still cannot authenticate (surfaced loudly by
  `sync_git.ps1` and the heartbeat — no longer silent).
- **Windows/PowerShell-5.1 gotchas, documented in `sync_git.ps1`:**
  `git config key ""` fails on a multi-valued key (must `--unset-all` first);
  PowerShell drops empty-string native args (the reset entry is added via
  `cmd`). `.gitattributes` pins `*.sh` to LF so the helper stays executable by
  git-bundled bash.

**When to revisit:** if the repo gains a GitHub remote requiring SSO, or if
PAT rotation becomes burdensome, reconsider an SSH deploy key or OIDC.
