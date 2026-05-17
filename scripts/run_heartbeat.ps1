# run_heartbeat.ps1
# Wrapper for Task Scheduler — runs the dead-man's-switch ~18:30 ET weekdays,
# after the EOD routine (16:15) has had ample time to finish.
#
# Task Scheduler action:
#   Program:   powershell.exe
#   Arguments: -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_heartbeat.ps1"
#   Start in:  C:\Users\schua\Personal\Projects\auto-trading
#
# Exit code is propagated: a non-zero exit (heartbeat raised an alert) also
# shows up as a failed run in Task Scheduler — a second, independent signal.

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"
$LogDir      = "$ProjectRoot\logs"
$Today       = (Get-Date -Format "yyyy-MM-dd")
$LogFile     = "$LogDir\heartbeat_$Today.log"
$VenvPython  = "$ProjectRoot\.venv\Scripts\python.exe"
$EnvFile     = "$ProjectRoot\.env"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Write-Log {
    param([string]$Message)
    $ts   = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Write-Log "=== Heartbeat Starting ==="
Write-Log "Date: $Today"
Set-Location $ProjectRoot

# ── Inject confirmed tool paths into PATH ─────────────────────────────────────
$env:PATH = @(
    "C:\Users\schua\AppData\Local\Programs\Python\Python311",
    "C:\Users\schua\AppData\Local\Programs\Python\Python311\Scripts",
    "C:\Users\schua\.local\bin",
    "C:\Program Files\Git\cmd",
    "C:\Program Files\Git\bin",
    $env:PATH
) -join ";"
$env:PATH = $env:PATH -replace ([regex]::Escape("C:\Users\schua\AppData\Local\Microsoft\WindowsApps") + ";?"), ""

if (-not (Test-Path $VenvPython)) {
    # No venv means pre-market never bootstrapped today — itself a red flag.
    Write-Log "ERROR: venv not found at $VenvPython — running heartbeat with system python."
    $VenvPython = "python"
}

# ── Load .env (GITHUB_TOKEN for the alert push, SMTP_* for the email) ─────────
if (Test-Path $EnvFile) {
    foreach ($line in (Get-Content $EnvFile)) {
        $line = $line.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { continue }
        $eqIndex = $line.IndexOf("=")
        if ($eqIndex -gt 0) {
            $key   = $line.Substring(0, $eqIndex).Trim()
            $value = $line.Substring($eqIndex + 1).Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Log ".env loaded."
} else {
    Write-Log "WARNING: .env not found — SMTP alert and headless push will be unavailable."
}

# ── Run the watchdog ──────────────────────────────────────────────────────────
Write-Log "Running heartbeat.py..."
& $VenvPython "$ProjectRoot\scripts\heartbeat.py" 2>&1 | ForEach-Object { Write-Log $_ }
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Log "=== Heartbeat raised an ALERT (exit $ExitCode) — see memory/health/ ==="
} else {
    Write-Log "=== Heartbeat OK ==="
}
exit $ExitCode
