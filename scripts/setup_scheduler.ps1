# Run this once as Administrator to register the Task Scheduler task.
# Right-click PowerShell -> Run as administrator, then:
#   powershell -ExecutionPolicy Bypass -File "C:\Users\schua\Personal\Projects\auto-trading\scripts\setup_scheduler.ps1"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"C:\Users\schua\Personal\Projects\auto-trading\scripts\run_pre_market.ps1`"" `
    -WorkingDirectory "C:\Users\schua\Personal\Projects\auto-trading"

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "7:30AM"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -WakeToRun

Register-ScheduledTask `
    -TaskName "AutoTrading-PreMarket" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ETF trading bot pre-market routine - runs daily at 7:30 AM ET on weekdays" `
    -RunLevel Highest `
    -Force

Write-Host "Task registered. Verify in Task Scheduler (taskschd.msc)."
