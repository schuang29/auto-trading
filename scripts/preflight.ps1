# preflight.ps1
# Read-only GO / NO-GO readiness check for the scheduled trading bot.
# Run before any scheduler/wrapper change and after editing scripts/. Safe to
# run anytime: it queries state, parses scripts, and dry-evaluates the
# heartbeat. It does NOT execute routines, push, alert, or email.
#
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\preflight.ps1
#
# Exit 0 = GO (all checks pass). Exit 1 = NO-GO (at least one failure).

$ErrorActionPreference = "Continue"
$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"
Set-Location $ProjectRoot

$script:fail = 0
function Pass($m) { Write-Host "  [OK]   $m" }
function Fail($m) { Write-Host "  [FAIL] $m"; $script:fail++ }

$VenvPy = "$ProjectRoot\.venv\Scripts\python.exe"
$Py = if (Test-Path $VenvPy) { $VenvPy } else { "python" }

Write-Host "==== 1. Scheduled tasks ===="
$tasks = "AutoTrading-PreMarket","AutoTrading-MarketOpen","AutoTrading-Midday","AutoTrading-EOD","AutoTrading-Weekly","AutoTrading-Heartbeat"
foreach ($n in $tasks) {
    $t = Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue
    if (-not $t) { Fail "$n MISSING"; continue }
    $i = Get-ScheduledTaskInfo -TaskName $n
    $s = $t.Settings
    $battery = (-not $s.DisallowStartIfOnBatteries) -and (-not $s.StopIfGoingOnBatteries)
    $trig = ($t.Triggers | ForEach-Object { $_.Enabled }) -join ","
    if ($t.State -eq "Disabled") { Fail "$n is Disabled" }
    elseif (-not $s.Enabled)     { Fail "$n settings disabled" }
    elseif (-not $battery)       { Fail "$n NOT battery-safe (would skip on battery)" }
    else { Pass ("{0} State={1} Battery=safe Wake={2} WhenAvail={3} TrigEn={4} Next={5}" -f $n,$t.State,$s.WakeToRun,$s.StartWhenAvailable,$trig,$i.NextRunTime) }
}

Write-Host "==== 2. Dependencies ===="
if (Test-Path $VenvPy) { Pass "venv python: $(& $VenvPy --version 2>&1)" } else { Fail "venv python missing ($VenvPy) - pre-market bootstraps it; OK only if first run" }
if (Get-Command git -ErrorAction SilentlyContinue) { Pass "git present" } else { Fail "git not on PATH" }
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) { foreach ($c in @("$env:USERPROFILE\.local\bin\claude.exe")) { if (Test-Path $c) { $claude = $c } } }
if ($claude) { Pass "claude CLI present" } else { Fail "claude CLI not found" }
foreach ($r in "pre_market","eod","midday","weekly") { if (Test-Path "$ProjectRoot\routines\$r.md") { Pass "routines/$r.md" } else { Fail "routines/$r.md MISSING" } }
if (Test-Path "$ProjectRoot\scripts\market_open.py") { Pass "scripts/market_open.py" } else { Fail "scripts/market_open.py MISSING" }

Write-Host "==== 3. .env required keys (values never printed) ===="
$envFile = "$ProjectRoot\.env"
if (-not (Test-Path $envFile)) { Fail ".env MISSING" }
else {
    $kv = @{}
    foreach ($line in (Get-Content $envFile)) {
        $l = $line.Trim()
        if ($l -eq "" -or $l.StartsWith("#")) { continue }
        $eq = $l.IndexOf("=")
        if ($eq -gt 0) { $kv[$l.Substring(0,$eq).Trim()] = $l.Substring($eq+1).Trim() }
    }
    foreach ($k in "ALPACA_API_KEY","ALPACA_SECRET_KEY","ALPACA_BASE_URL","GITHUB_TOKEN","SMTP_HOST","SMTP_PORT","SMTP_USER","SMTP_PASS","NOTIFY_EMAIL_TO") {
        if ($kv.ContainsKey($k) -and $kv[$k].Length -gt 0) { Pass "$k set" } else { Fail "$k missing/empty" }
    }
}

Write-Host "==== 4. All scripts/*.ps1 ASCII + powershell.exe parse ===="
$ps1 = Get-ChildItem "$ProjectRoot\scripts\*.ps1" | ForEach-Object { $_.FullName }
& $Py "$ProjectRoot\scripts\check_ps1.py" --full @ps1
if ($LASTEXITCODE -eq 0) { Pass "all scripts/*.ps1 clean" } else { Fail "check_ps1.py reported problems (see above)" }

Write-Host "==== 5. Heartbeat dry-evaluation (read-only) ===="
$hb = & $Py -c "import sys; sys.path.insert(0,r'$ProjectRoot\scripts'); import heartbeat; from datetime import datetime; from pathlib import Path; s,r,d=heartbeat.evaluate(datetime.now(),Path(r'$ProjectRoot'),0); print(s); [print('   reason:',x) for x in r]"
$hbStatus = ($hb | Select-Object -First 1)
if ($hbStatus -eq "ok" -or $hbStatus -eq "skip") { Pass "heartbeat dry-eval: $hbStatus" }
else { Fail "heartbeat dry-eval: $hbStatus"; $hb | Select-Object -Skip 1 | ForEach-Object { Write-Host "         $_" } }

Write-Host "==== 6. Audit trail synced ===="
git fetch origin main --quiet 2>$null
$unpushed = (git rev-list --count origin/main..HEAD 2>$null)
if ($unpushed -eq "0") { Pass "origin/main..HEAD = 0 (synced)" } else { Fail "unpushed commits: $unpushed (audit trail not on origin)" }

Write-Host ""
if ($script:fail -eq 0) { Write-Host "==== RESULT: GO (all checks passed) ===="; exit 0 }
else { Write-Host "==== RESULT: NO-GO ($script:fail failing check(s)) ===="; exit 1 }
