# run_pre_market.ps1
# Wrapper script for Task Scheduler — handles PATH, venv, logging, and Windows date.
#
# Task Scheduler action:
#   Program:   powershell.exe
#   Arguments: -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_pre_market.ps1"
#   Start in:  C:\Users\schua\Personal\Projects\auto-trading

$ErrorActionPreference = "Stop"

# ── All paths declared upfront ────────────────────────────────────────────────
$PythonExe   = "C:\Users\schua\AppData\Local\Programs\Python\Python311\python.exe"
$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"
$LogDir      = "$ProjectRoot\logs"
$Today       = (Get-Date -Format "yyyy-MM-dd")
$LogFile     = "$LogDir\pre_market_$Today.log"
$VenvPython  = "$ProjectRoot\.venv\Scripts\python.exe"
$VenvPip     = "$ProjectRoot\.venv\Scripts\pip.exe"
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

Write-Log "=== Pre-Market Routine Starting ==="
Write-Log "Date: $Today"
Write-Log "Project root: $ProjectRoot"
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

# Strip the WindowsApps Python stub — opens the Store instead of running Python
$env:PATH = $env:PATH -replace ([regex]::Escape("C:\Users\schua\AppData\Local\Microsoft\WindowsApps") + ";?"), ""

# ── Verify required tools ─────────────────────────────────────────────────────
$allFound = $true

if (Test-Path $PythonExe) {
    $pyVersion = & $PythonExe --version 2>&1
    Write-Log "OK: python -> $PythonExe ($pyVersion)"
} else {
    Write-Log "MISSING: python not found at $PythonExe"
    $allFound = $false
}

foreach ($tool in @("git", "claude")) {
    $found = Get-Command $tool -ErrorAction SilentlyContinue
    if ($found) {
        Write-Log "OK: $tool -> $($found.Source)"
    } else {
        Write-Log "MISSING: $tool not found in PATH"
        $allFound = $false
    }
}

if (-not $allFound) {
    Write-Log "ERROR: One or more required tools missing. Aborting."
    exit 1
}

# ── Set up venv if it doesn't exist ───────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Log "Creating virtual environment..."
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Log "ERROR: venv creation failed."; exit 1 }

    Write-Log "Installing requirements..."
    & $VenvPip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) { Write-Log "ERROR: pip install failed."; exit 1 }

    Write-Log "Venv ready."
} else {
    Write-Log "Venv OK — skipping creation."
}

# ── Load .env into process environment ────────────────────────────────────────
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
    Write-Log "WARNING: .env not found at $EnvFile — API calls will fail."
}

# ── Run Claude Code pre-market routine ────────────────────────────────────────
# --dangerously-skip-permissions: allows Claude Code to write files and run
# commands without interactive prompts. Safe here because this is a controlled,
# local project with a restricted guardrails layer. Required for unattended
# scheduled runs where nobody is present to approve prompts.
Write-Log "Launching Claude Code pre-market routine..."

$ClaudePrompt = (
    "You are the pre-market routine for an autonomous ETF trading bot. " +
    "The full instructions are in routines/pre_market.md - read and follow them exactly, step by step. " +
    "Use the venv python at .venv\Scripts\python.exe for all python commands. " +
    "After completing all 7 steps, commit and push the daily memory log: " +
    "git add memory/daily/ && git commit -m 'memory: pre-market log $Today' && git push origin main. " +
    "If any step fails, log the failure to memory/daily/ and continue. Do not abort for a single failure."
)

claude --dangerously-skip-permissions --print $ClaudePrompt
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Log "ERROR: Claude Code exited with code $ExitCode"
    exit $ExitCode
}

Write-Log "=== Pre-Market Routine Completed Successfully ==="
