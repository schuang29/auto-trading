# Run this once as Administrator to register all Task Scheduler tasks.
# Right-click PowerShell -> Run as administrator, then:
#   powershell -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\setup_scheduler.ps1"
#
# Safe to re-run: -Force overwrites existing task registrations without error.
# Tasks registered: AutoTrading-PreMarket, AutoTrading-MarketOpen, AutoTrading-EOD

$ProjectRoot = "C:\Users\schua\Personal\Projects\auto-trading"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -WakeToRun

# ── Pre-market: 7:30 AM ET, weekdays ─────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ProjectRoot\scripts\run_pre_market.ps1`"" `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "7:30AM"

Register-ScheduledTask `
    -TaskName "AutoTrading-PreMarket" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ETF trading bot pre-market routine - 7:30 AM ET weekdays" `
    -RunLevel Highest `
    -Force

Write-Host "Registered: AutoTrading-PreMarket (7:30 AM)"

# ── Market-open: 9:35 AM ET, weekdays ────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ProjectRoot\scripts\run_market_open.ps1`"" `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "9:35AM"

Register-ScheduledTask `
    -TaskName "AutoTrading-MarketOpen" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ETF trading bot market-open execution - 9:35 AM ET weekdays" `
    -RunLevel Highest `
    -Force

Write-Host "Registered: AutoTrading-MarketOpen (9:35 AM)"

# ── EOD: 4:15 PM ET, weekdays ─────────────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ProjectRoot\scripts\run_eod.ps1`"" `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "4:15PM"

Register-ScheduledTask `
    -TaskName "AutoTrading-EOD" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ETF trading bot EOD routine - 4:15 PM ET weekdays" `
    -RunLevel Highest `
    -Force

Write-Host "Registered: AutoTrading-EOD (4:15 PM)"

Write-Host ""
Write-Host "All tasks registered. Verify in Task Scheduler (taskschd.msc)."
