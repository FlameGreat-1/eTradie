<#
.SYNOPSIS
    Quick health check for the MT5 VPS setup.

.DESCRIPTION
    Reads the health_status.json written by monitor_mt5.ps1 and displays
    a summary. Also checks MT5 process directly and reviews recent EA
    log entries for errors.

    Run this via RDP or as a quick diagnostic when troubleshooting.

.PARAMETER StatusFile
    Path to health_status.json. Default: C:\eTradie\health_status.json

.PARAMETER LogDir
    Path to monitor log directory. Default: C:\eTradie\logs
#>

param(
    [string]$StatusFile = "C:\eTradie\health_status.json",
    [string]$LogDir = "C:\eTradie\logs"
)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  eTradie VPS Health Check" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# 1. MT5 Process
# ---------------------------------------------------------------------------
Write-Host "--- MT5 Process ---" -ForegroundColor Cyan
$mt5 = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($mt5) {
    $uptime = (New-TimeSpan -Start $mt5.StartTime -End (Get-Date))
    $uptimeStr = "{0}d {1}h {2}m" -f $uptime.Days, $uptime.Hours, $uptime.Minutes
    Write-Host "  Status:  " -NoNewline; Write-Host "RUNNING" -ForegroundColor Green
    Write-Host "  PID:     $($mt5.Id)"
    Write-Host "  Memory:  $([math]::Round($mt5.WorkingSet64 / 1MB, 1)) MB"
    Write-Host "  CPU:     $([math]::Round($mt5.CPU, 1)) seconds"
    Write-Host "  Uptime:  $uptimeStr"
    Write-Host "  Started: $($mt5.StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
} else {
    Write-Host "  Status:  " -NoNewline; Write-Host "NOT RUNNING" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# 2. Monitor Status
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- Monitor Status ---" -ForegroundColor Cyan
if (Test-Path $StatusFile) {
    try {
        $status = Get-Content $StatusFile -Raw | ConvertFrom-Json
        $statusColor = switch ($status.status) {
            "healthy"   { "Green" }
            "recovered" { "Yellow" }
            default     { "Red" }
        }
        Write-Host "  Status:       " -NoNewline; Write-Host $status.status -ForegroundColor $statusColor
        Write-Host "  Last Check:   $($status.last_check)"
        Write-Host "  Last Action:  $($status.last_action)"
        Write-Host "  Failures:     $($status.consecutive_failures)"
        if ($status.alert) {
            Write-Host "  ALERT:        " -NoNewline; Write-Host "YES - MT5 has been down repeatedly!" -ForegroundColor Red
        }
        if ($status.last_error) {
            Write-Host "  Last Error:   $($status.last_error)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Failed to parse status file: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  Status file not found: $StatusFile" -ForegroundColor Yellow
    Write-Host "  Monitor may not be installed. Run install_monitor_task.ps1" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 3. Scheduled Task
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- Monitor Scheduled Task ---" -ForegroundColor Cyan
$task = Get-ScheduledTask -TaskName "eTradie MT5 Health Monitor" -TaskPath "\eTradie\" -ErrorAction SilentlyContinue
if ($task) {
    $taskColor = if ($task.State -eq "Ready") { "Green" } else { "Yellow" }
    Write-Host "  State:   " -NoNewline; Write-Host $task.State -ForegroundColor $taskColor
    $taskInfo = Get-ScheduledTaskInfo -TaskName "eTradie MT5 Health Monitor" -TaskPath "\eTradie\" -ErrorAction SilentlyContinue
    if ($taskInfo) {
        Write-Host "  Last Run: $($taskInfo.LastRunTime)"
        Write-Host "  Result:   $($taskInfo.LastTaskResult)"
    }
} else {
    Write-Host "  Task not found. Run install_monitor_task.ps1" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 4. Firewall Rule
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- Firewall Rule ---" -ForegroundColor Cyan
$fwRule = Get-NetFirewallRule -DisplayName "eTradie ZeroMQ EA*" -ErrorAction SilentlyContinue
if ($fwRule) {
    $filter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $fwRule
    $portFilter = Get-NetFirewallPortFilter -AssociatedNetFirewallRule $fwRule
    Write-Host "  Status:     " -NoNewline; Write-Host $fwRule.Enabled -ForegroundColor Green
    Write-Host "  Port:       $($portFilter.LocalPort)"
    Write-Host "  Allowed IP: $($filter.RemoteAddress)"
} else {
    Write-Host "  Rule not found. Run setup_vps.ps1" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# 5. Network Listener
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- ZeroMQ Port Listener ---" -ForegroundColor Cyan
$listener = Get-NetTCPConnection -LocalPort 5555 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "  Port 5555: " -NoNewline; Write-Host "LISTENING" -ForegroundColor Green
    Write-Host "  PID:       $($listener.OwningProcess)"
} else {
    Write-Host "  Port 5555: " -NoNewline; Write-Host "NOT LISTENING" -ForegroundColor Red
    Write-Host "  EA may not be attached to a chart, or MT5 is not running." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 6. Recent Monitor Log
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- Recent Monitor Log (last 10 lines) ---" -ForegroundColor Cyan
$monitorLog = Join-Path $LogDir "mt5_monitor.log"
if (Test-Path $monitorLog) {
    Get-Content $monitorLog -Tail 10 | ForEach-Object {
        $color = "White"
        if ($_ -match "\[ERROR\]") { $color = "Red" }
        elseif ($_ -match "\[WARN\]") { $color = "Yellow" }
        elseif ($_ -match "\[CRITICAL\]") { $color = "Red" }
        Write-Host "  $_" -ForegroundColor $color
    }
} else {
    Write-Host "  No monitor log found at: $monitorLog" -ForegroundColor Yellow
}

Write-Host ""
