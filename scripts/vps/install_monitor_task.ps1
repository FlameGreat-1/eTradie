#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Register the MT5 health monitor as a Windows Scheduled Task.

.DESCRIPTION
    Creates a scheduled task that runs monitor_mt5.ps1 every 60 seconds.
    The task runs under the SYSTEM account so it survives logoff and
    continues after reboot without requiring an interactive session
    for the monitoring itself.

    MT5 still requires a desktop session (handled by auto-login in
    setup_vps.ps1). This task monitors and restarts MT5 if it crashes.

.PARAMETER Action
    'install' to create the task, 'uninstall' to remove it.

.PARAMETER MonitorScript
    Path to monitor_mt5.ps1. Default: C:\eTradie\scripts\monitor_mt5.ps1

.PARAMETER IntervalSeconds
    How often the monitor runs. Default: 60.
#>

param(
    [ValidateSet("install", "uninstall")]
    [string]$Action = "install",

    [string]$MonitorScript = "C:\eTradie\scripts\monitor_mt5.ps1",

    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"
$taskName = "eTradie MT5 Health Monitor"
$taskPath = "\eTradie\"

if ($Action -eq "uninstall") {
    $existing = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false
        Write-Host "[OK] Scheduled task '$taskName' removed." -ForegroundColor Green
    } else {
        Write-Host "[INFO] Task '$taskName' not found. Nothing to remove." -ForegroundColor Yellow
    }
    exit 0
}

# Install
if (-not (Test-Path $MonitorScript)) {
    Write-Host "[FAIL] Monitor script not found: $MonitorScript" -ForegroundColor Red
    Write-Host "  Copy monitor_mt5.ps1 to C:\eTradie\scripts\ first." -ForegroundColor Yellow
    exit 1
}

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false
    Write-Host "[INFO] Removed existing task for re-creation." -ForegroundColor Yellow
}

# Build the task
$taskAction = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$MonitorScript`"" `
    -WorkingDirectory (Split-Path $MonitorScript -Parent)

$taskTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Seconds $IntervalSeconds) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 30) `
    -MultipleInstances IgnoreNew

$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $taskName `
    -TaskPath $taskPath `
    -Action $taskAction `
    -Trigger $taskTrigger `
    -Settings $taskSettings `
    -Principal $taskPrincipal `
    -Description "Monitors MT5 terminal process and auto-restarts if crashed. Part of eTradie VPS deployment." | Out-Null

Write-Host ""
Write-Host "[OK] Scheduled task '$taskName' created." -ForegroundColor Green
Write-Host "  Interval: every $IntervalSeconds seconds" -ForegroundColor White
Write-Host "  Script:   $MonitorScript" -ForegroundColor White
Write-Host "  Account:  SYSTEM" -ForegroundColor White
Write-Host "  Status:   $(Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath | Select-Object -ExpandProperty State)" -ForegroundColor White
Write-Host ""
Write-Host "  To check status:  Get-ScheduledTask -TaskName '$taskName' -TaskPath '$taskPath'" -ForegroundColor Gray
Write-Host "  To run manually:  Start-ScheduledTask -TaskName '$taskName' -TaskPath '$taskPath'" -ForegroundColor Gray
Write-Host "  To uninstall:     .\install_monitor_task.ps1 -Action uninstall" -ForegroundColor Gray
