# run_market_open.ps1
# Wrapper script for Task Scheduler — runs at 9:35 AM ET on weekdays.
# Reads today's proposals from memory/proposals/ and executes them on Alpaca paper.
#
# Task Scheduler action:
#   Program:   powershell.exe
#   Arguments: -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\run_market_open.ps1"
#   Start in:  C:\Users\schua\Personal\Projects\auto-trading

$ErrorActionPreference = "Stop"

# ── All paths declared upfront ────────────────────────────────────────────────
$PythonExe   = "C:\Users\schua\AppData\Local\Programs\Python\Python311\python.exe"
$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"
$LogDir      = "$ProjectRoot\logs"
$Today       = (Get-Date -Format "yyyy-MM-dd")
$LogFile     = "$LogDir\market_open_$Today.log"
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

Write-Log "=== Market-Open Routine Starting ==="
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

# ── Verify venv exists ────────────────────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Log "ERROR: venv not found at $VenvPython - run the pre-market routine first."
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

# ── Verify today's proposals file exists ──────────────────────────────────────
$ProposalsFile = "$ProjectRoot\memory\proposals\$Today.json"
if (-not (Test-Path $ProposalsFile)) {
    Write-Log "ERROR: No proposals file at $ProposalsFile"
    Write-Log "The pre-market routine must complete first. Aborting."
    exit 1
}
Write-Log "Proposals file found: $ProposalsFile"

# ── Execute market-open script ────────────────────────────────────────────────
Write-Log "Running market_open.py..."
& $VenvPython "$ProjectRoot\scripts\market_open.py"
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Log "ERROR: market_open.py exited with code $ExitCode"
    exit $ExitCode
}

# ── Commit decisions and positions to git ─────────────────────────────────────
Write-Log "Committing memory updates..."
git add memory/decisions/ memory/positions.md
$HasChanges = git diff --cached --quiet; $HasChanges = -not $?
if ($HasChanges) {
    git commit -m "memory: market-open execution $Today"
    git push origin main
    Write-Log "Memory committed and pushed."
} else {
    Write-Log "No memory changes to commit (no orders placed)."
}

Write-Log "=== Market-Open Routine Completed Successfully ==="
