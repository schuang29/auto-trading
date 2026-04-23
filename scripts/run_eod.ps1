# run_eod.ps1
# Wrapper script for Task Scheduler — runs at 4:15 PM ET on weekdays.
# Invokes the EOD routine via Claude Code, commits memory updates to GitHub.
#
# Task Scheduler action:
#   Program:   powershell.exe
#   Arguments: -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_eod.ps1"
#   Start in:  C:\Users\schua\Personal\Projects\auto-trading

$ErrorActionPreference = "Stop"

# ── All paths declared upfront ────────────────────────────────────────────────
$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"
$LogDir      = "$ProjectRoot\logs"
$Today       = (Get-Date -Format "yyyy-MM-dd")
$LogFile     = "$LogDir\eod_$Today.log"
$VenvPython  = "$ProjectRoot\.venv\Scripts\python.exe"
$EnvFile     = "$ProjectRoot\.env"

# ── Ensure logs directory exists ──────────────────────────────────────────────
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Write-Log {
    param([string]$Message)
    $ts   = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Write-Log "=== EOD Routine Starting ==="
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

# ── Verify required tools ─────────────────────────────────────────────────────
foreach ($tool in @("git", "claude")) {
    $found = Get-Command $tool -ErrorAction SilentlyContinue
    if (-not $found) {
        Write-Log "ERROR: $tool not found in PATH. Aborting."
        exit 1
    }
    Write-Log "OK: $tool -> $($found.Source)"
}

if (-not (Test-Path $VenvPython)) {
    Write-Log "ERROR: venv not found at $VenvPython. Run pre-market first."
    exit 1
}

# ── Load .env ─────────────────────────────────────────────────────────────────
if (Test-Path $EnvFile) {
    Write-Log "Loading .env..."
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
    Write-Log "ERROR: .env not found at $EnvFile"
    exit 1
}

# ── Run Claude Code EOD routine ───────────────────────────────────────────────
Write-Log "Launching Claude Code EOD routine..."

$ClaudePrompt = (
    "You are the EOD routine for an autonomous ETF trading bot. " +
    "The full instructions are in routines/eod.md - read and follow them exactly, step by step. " +
    "Use the venv python at .venv\Scripts\python.exe for all python commands. " +
    "After completing all 6 steps, commit and push memory updates: " +
    "git add memory/daily/ memory/positions.md memory/highwatermarks.json && " +
    "git commit -m 'memory: EOD log $Today' && git push origin main. " +
    "If any step fails, log the failure to memory/daily/ and continue."
)

claude --dangerously-skip-permissions --model claude-sonnet-4-6 --print $ClaudePrompt
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Log "ERROR: Claude Code exited with code $ExitCode"
    exit $ExitCode
}

Write-Log "=== EOD Routine Completed Successfully ==="
