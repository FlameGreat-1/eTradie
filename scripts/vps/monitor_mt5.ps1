<#
.SYNOPSIS
    eTradie MT5 Health Monitor - Auto-recovery watchdog for the VPS.

.DESCRIPTION
    Runs as a Windows Scheduled Task every 60 seconds. Checks if the
    MT5 terminal process (terminal64.exe) is running. If not, restarts
    it automatically.

    Features:
    - Process existence check
    - Auto-restart with configurable delay
    - Consecutive failure tracking with alert threshold
    - Health status JSON file for external monitoring
    - Rotating log file (max 10MB, keeps last 5)
    - Graceful handling of MT5 already starting up

    The health status JSON file can be read by an external monitoring
    system or the eTradie dashboard to show VPS EA status.

.PARAMETER MT5InstallPath
    MT5 installation directory. Default: C:\Program Files\MetaTrader 5

.PARAMETER MaxConsecutiveFailures
    Number of consecutive failures before writing an alert flag.
    Default: 3 (= 3 minutes of MT5 being down).

.PARAMETER LogDir
    Directory for log files. Default: C:\eTradie\logs

.PARAMETER StatusFile
    Path to the health status JSON file. Default: C:\eTradie\health_status.json
#>

param(
    [string]$MT5InstallPath = "C:\Program Files\MetaTrader 5",
    [int]$MaxConsecutiveFailures = 3,
    [string]$LogDir = "C:\eTradie\logs",
    [string]$StatusFile = "C:\eTradie\health_status.json"
)

$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# Ensure directories exist
# ---------------------------------------------------------------------------
foreach ($dir in @($LogDir, (Split-Path $StatusFile -Parent))) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# ---------------------------------------------------------------------------
# Logging with rotation
# ---------------------------------------------------------------------------
$logFile = Join-Path $LogDir "mt5_monitor.log"
$maxLogSize = 10MB
$maxLogFiles = 5

function Write-Log {
    param([string]$Level, [string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC"
    $line = "[$timestamp] [$Level] $Message"

    # Rotate if needed
    if ((Test-Path $logFile) -and (Get-Item $logFile).Length -gt $maxLogSize) {
        for ($i = $maxLogFiles; $i -ge 1; $i--) {
            $old = "$logFile.$i"
            $new = "$logFile.$($i + 1)"
            if (Test-Path $old) {
                if ($i -eq $maxLogFiles) {
                    Remove-Item $old -Force
                } else {
                    Move-Item $old $new -Force
                }
            }
        }
        Move-Item $logFile "$logFile.1" -Force
    }

    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# ---------------------------------------------------------------------------
# State tracking (persisted between runs via status file)
# ---------------------------------------------------------------------------
function Get-State {
    if (Test-Path $StatusFile) {
        try {
            return Get-Content $StatusFile -Raw | ConvertFrom-Json
        } catch {
            return $null
        }
    }
    return $null
}

function Save-State {
    param(
        [string]$Status,
        [bool]$MT5Running,
        [int]$ConsecutiveFailures,
        [string]$LastAction,
        [string]$LastError
    )

    $state = @{
        status               = $Status
        mt5_running          = $MT5Running
        mt5_pid              = 0
        consecutive_failures = $ConsecutiveFailures
        last_check           = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        last_action          = $LastAction
        last_error           = $LastError
        alert                = ($ConsecutiveFailures -ge $MaxConsecutiveFailures)
        uptime_seconds       = 0
        mt5_install_path     = $MT5InstallPath
    }

    # Get MT5 process info if running
    $proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($proc) {
        $state.mt5_pid = $proc.Id
        try {
            $state.uptime_seconds = [int](New-TimeSpan -Start $proc.StartTime -End (Get-Date)).TotalSeconds
        } catch {}
    }

    $state | ConvertTo-Json -Depth 3 | Set-Content -Path $StatusFile -Encoding UTF8
}

# ---------------------------------------------------------------------------
# Main health check
# ---------------------------------------------------------------------------
$previousState = Get-State
$consecutiveFailures = 0
if ($previousState -and $previousState.consecutive_failures) {
    $consecutiveFailures = [int]$previousState.consecutive_failures
}

$mt5Exe = Join-Path $MT5InstallPath "terminal64.exe"
$mt5Process = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue

if ($mt5Process) {
    # MT5 is running
    $consecutiveFailures = 0
    Save-State -Status "healthy" -MT5Running $true -ConsecutiveFailures 0 `
        -LastAction "health_check_passed" -LastError ""
    Write-Log "INFO" "MT5 running (PID: $($mt5Process.Id), Memory: $([math]::Round($mt5Process.WorkingSet64 / 1MB, 1))MB)"
}
else {
    # MT5 is NOT running
    $consecutiveFailures++
    Write-Log "WARN" "MT5 not running (consecutive failures: $consecutiveFailures)"

    # Check if MT5 executable exists
    if (-not (Test-Path $mt5Exe)) {
        Write-Log "ERROR" "MT5 executable not found at: $mt5Exe"
        Save-State -Status "error" -MT5Running $false -ConsecutiveFailures $consecutiveFailures `
            -LastAction "executable_not_found" -LastError "terminal64.exe not found at $MT5InstallPath"
        exit 1
    }

    # Auto-restart MT5
    Write-Log "INFO" "Attempting to restart MT5..."
    try {
        Start-Process -FilePath $mt5Exe -ArgumentList "/portable" -WorkingDirectory $MT5InstallPath
        Start-Sleep -Seconds 5  # Give MT5 time to start

        # Verify it started
        $newProc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
        if ($newProc) {
            Write-Log "INFO" "MT5 restarted successfully (PID: $($newProc.Id))"
            Save-State -Status "recovered" -MT5Running $true -ConsecutiveFailures $consecutiveFailures `
                -LastAction "auto_restart_success" -LastError ""
        } else {
            Write-Log "ERROR" "MT5 failed to start after restart attempt"
            Save-State -Status "error" -MT5Running $false -ConsecutiveFailures $consecutiveFailures `
                -LastAction "auto_restart_failed" -LastError "Process did not appear after 5 seconds"
        }
    } catch {
        Write-Log "ERROR" "Failed to start MT5: $_"
        Save-State -Status "error" -MT5Running $false -ConsecutiveFailures $consecutiveFailures `
            -LastAction "auto_restart_exception" -LastError $_.ToString()
    }

    # Alert if threshold exceeded
    if ($consecutiveFailures -ge $MaxConsecutiveFailures) {
        Write-Log "CRITICAL" "MT5 has been down for $consecutiveFailures consecutive checks. ALERT TRIGGERED."
    }
}
