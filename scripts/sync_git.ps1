# sync_git.ps1
# Shared push-and-verify step for every routine wrapper.
#
# Why this exists: the bot's audit trail is only durable once it reaches
# origin. The scheduled (non-interactive) context cannot use the Windows
# Credential Manager ("wincredman") store, so every push silently failed
# 2026-05-12 onward and the failure was only ever written to a *local* note
# that itself never got pushed. This script:
#   1. Ensures a local git credential helper that authenticates headless
#      using $env:GITHUB_TOKEN (a fine-grained PAT from .env), falling
#      through to the interactive 'manager' helper when the token is absent.
#   2. Pushes origin/main and VERIFIES nothing is left unpushed.
#   3. On failure, makes it LOUD: a committed-intent health marker, an SMTP
#      alert, and a non-zero exit - never a silent local-only note again.
#
# Safe to call every run: the credential-helper config is rebuilt
# deterministically (idempotent), and the push is a no-op when already synced.
#
# Returns exit 0 on a verified-synced repo, exit 1 otherwise.

param(
    [string]$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading",
    [string]$Context     = "routine"   # e.g. "pre-market", "eod" - for the alert
)

$ErrorActionPreference = "Continue"
Set-Location $ProjectRoot

function Sg-Log { param([string]$m) Write-Host "[sync_git] $m" }

# -- 1. Ensure headless-capable credential helper (idempotent) -----------------
# Rebuild the local helper chain deterministically every call so it self-heals
# if .git/config is ever clobbered. Final chain:
#   [ ""(reset, drops inherited global manager), env-token script, manager ]
#   -> git evaluates as [ env-token, manager ]
# The env-token helper (scripts/git-credential-env.sh) emits the PAT only for
# `get` and only when GITHUB_TOKEN is set; otherwise it is silent so git falls
# through to 'manager' for interactive use. The PAT is NEVER written to
# .git/config - only this script's path is - and .git/config is not committed.
#
# Two Windows/PowerShell-5.1 gotchas this sequence works around, learned the
# hard way: (a) `git config key ""` FAILS on a multi-valued key, so we
# --unset-all first; (b) PowerShell drops empty-string native args, so the
# reset entry is added via cmd, which passes "" correctly.
$prFwd      = $ProjectRoot -replace '\\','/'
$credHelper = "!sh $prFwd/scripts/git-credential-env.sh"
git config --local --unset-all credential.helper 2>$null | Out-Null
cmd /c 'git config --local --add credential.helper ""' | Out-Null
git config --local --add credential.helper $credHelper | Out-Null
git config --local --add credential.helper "manager"   | Out-Null

if (-not $env:GITHUB_TOKEN) {
    Sg-Log "WARNING: GITHUB_TOKEN not in environment - headless push will fall back to 'manager' and likely fail in the scheduled context."
}

# -- 2. Push and verify --------------------------------------------------------
Sg-Log "Pushing origin main..."
git push origin main 2>&1 | ForEach-Object { Sg-Log $_ }

git fetch origin main --quiet 2>&1 | Out-Null
$unpushed = (git rev-list --count origin/main..HEAD 2>$null)
if (-not $unpushed) { $unpushed = "unknown" }

if ($unpushed -eq "0") {
    Sg-Log "OK: repo verified in sync with origin/main (0 unpushed commits)."
    exit 0
}

# -- 3. Failure: make it loud --------------------------------------------------
$ts      = Get-Date -Format "yyyy-MM-dd_HHmmss"
$today   = Get-Date -Format "yyyy-MM-dd"
$health  = "$ProjectRoot\memory\health"
if (-not (Test-Path $health)) { New-Item -ItemType Directory -Path $health | Out-Null }
$marker  = "$health\PUSH-FAILED-$ts.md"

$headSha = (git rev-parse --short HEAD 2>$null)
$body = @"
# AUDIT-TRAIL PUSH FAILURE

**When:** $ts (local)
**Context:** $Context routine
**Unpushed commits (origin/main..HEAD):** $unpushed
**Local HEAD:** $headSha

The routine completed but its commits did NOT reach origin/main. The audit
trail is local-only until this is resolved. Likely cause: GITHUB_TOKEN missing
or invalid in .env (headless context cannot use the Windows Credential Manager).

Action:
  1. Confirm GITHUB_TOKEN is set in .env (fine-grained PAT, Contents: R/W).
  2. Run:  git push origin main
  3. Check scripts/sync_git.ps1 credential-helper config if it recurs.
"@
Set-Content -Path $marker -Value $body -Encoding utf8
Sg-Log "WROTE health marker: $marker"

# Commit the marker so the *failure itself* is in the (eventual) audit trail,
# then try once more to push everything including the marker.
git add memory/health/ 2>&1 | Out-Null
git commit -m "health: audit-trail push failure ($Context $today)" 2>&1 | ForEach-Object { Sg-Log $_ }
git push origin main 2>&1 | ForEach-Object { Sg-Log $_ }

# SMTP alert (best-effort; never blocks - local marker + non-zero exit are the
# guaranteed channels). notify.py exits 2 when SMTP isn't configured yet.
$venvPy = "$ProjectRoot\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $subject = "PUSH FAILURE - $Context $today"
    & $venvPy "$ProjectRoot\scripts\notify.py" --subject $subject --body $body 2>&1 | ForEach-Object { Sg-Log $_ }
} else {
    Sg-Log "venv python missing - skipped SMTP alert (local marker still written)."
}

Sg-Log "FAIL: $unpushed commit(s) still unpushed. See $marker"
exit 1
