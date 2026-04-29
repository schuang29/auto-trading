# run_weekly.ps1
# Wrapper script for Task Scheduler — runs at 5:00 PM ET on Fridays (after EOD).
# Invokes the weekly review routine via Claude Code, commits the review file to GitHub.
#
# Task Scheduler action:
#   Program:   powershell.exe
#   Arguments: -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_weekly.ps1"
#   Start in:  C:\Users\schua\Personal\Projects\auto-trading

$ErrorActionPreference = "Stop"

# ── All paths declared upfront ────────────────────────────────────────────────
$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"
$LogDir      = "$ProjectRoot\logs"
$Today       = (Get-Date -Format "yyyy-MM-dd")
$LogFile     = "$LogDir\weekly_$Today.log"
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

Write-Log "=== Weekly Review Routine Starting ==="
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
    Write-Log "ERROR: venv not found at $VenvPython. Run pre-market first to bootstrap."
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

# ── Run Claude Code weekly review routine ─────────────────────────────────────
# Uses Opus for higher-quality analysis: regime accuracy assessment, performance
# attribution, and proposed strategy adjustments benefit from Opus reasoning.
# This routine runs once per week so the cost is acceptable.
Write-Log "Launching Claude Code weekly review routine..."

$ClaudePrompt = (
    "You are the weekly review routine for an autonomous ETF trading bot. " +
    "The full instructions are in routines/weekly.md - read and follow them exactly, step by step. " +
    "Use the venv python at .venv\Scripts\python.exe for all python commands. " +
    "After completing all 7 steps, commit and push the new weekly review file: " +
    "git add memory/weekly/ && " +
    "git commit -m 'memory: weekly review $Today' && git push origin main. " +
    "If any step fails, note the failure in the weekly review file under a 'Routine errors' section and continue."
)

claude --dangerously-skip-permissions --model claude-opus-4-7 --print $ClaudePrompt
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Log "ERROR: Claude Code exited with code $ExitCode"
    exit $ExitCode
}

Write-Log "=== Weekly Review Routine Completed Successfully ==="
