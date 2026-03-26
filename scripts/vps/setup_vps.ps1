#Requires -RunAsAdministrator
<#
.SYNOPSIS
    eTradie VPS Setup - Master automation script for Contabo Windows VPS.

.DESCRIPTION
    Automates the complete MT5 + ZeroMQ EA deployment on a Windows VPS.
    Covers Steps 2-7 from docs/vps/deployement_guide.md:
      - Windows hardening (firewall, services, timezone)
      - ZeroMQ EA dependency installation (mql-zmq, JAson)
      - EA file deployment
      - MT5 auto-start configuration (startup shortcut, auto-login, power plan)
      - Post-setup verification

    Prerequisites:
      - Windows Server 2022 on Contabo VPS
      - MT5 terminal installed (Step 3 from guide)
      - MT5 data folder path known (File > Open Data Folder in MT5)
      - Run this script as Administrator

.PARAMETER MT5DataFolder
    Full path to the MT5 data folder.
    Example: C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\ABC123DEF

.PARAMETER LinuxMachineIP
    Public IP of the Linux machine running the eTradie Docker stack.
    Used to restrict firewall rule to this IP only.

.PARAMETER ZmqPort
    ZeroMQ port the EA listens on. Default: 5555.

.PARAMETER MT5InstallPath
    MT5 installation directory. Default: C:\Program Files\MetaTrader 5

.PARAMETER VPSPassword
    Administrator password for auto-login configuration.
    Required for MT5 to auto-start after VPS reboot.

.PARAMETER EASourcePath
    Path to ZeroMQ_EA.mq5 file. If not provided, downloads from the repo.

.EXAMPLE
    .\setup_vps.ps1 `
        -MT5DataFolder "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\ABC123" `
        -LinuxMachineIP "203.0.113.50" `
        -VPSPassword "MyStr0ngP@ss!"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$MT5DataFolder,

    [Parameter(Mandatory=$true)]
    [string]$LinuxMachineIP,

    [int]$ZmqPort = 5555,

    [string]$MT5InstallPath = "C:\Program Files\MetaTrader 5",

    [Parameter(Mandatory=$true)]
    [string]$VPSPassword,

    [string]$EASourcePath = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Speed up Invoke-WebRequest

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
function Write-Step  { param([string]$msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok    { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn  { param([string]$msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail  { param([string]$msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info  { param([string]$msg) Write-Host "  $msg" -ForegroundColor White }

$logFile = "$env:USERPROFILE\Desktop\etradie_vps_setup_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $logFile -Append

Write-Host "`n" -NoNewline
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  eTradie VPS Setup - MT5 + ZeroMQ EA Deployment" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------
Write-Step "Validating inputs"

if (-not (Test-Path $MT5DataFolder)) {
    Write-Fail "MT5 data folder not found: $MT5DataFolder"
    Write-Info "Launch MT5 > File > Open Data Folder to find the correct path."
    Stop-Transcript
    exit 1
}
Write-Ok "MT5 data folder exists: $MT5DataFolder"

if (-not (Test-Path "$MT5InstallPath\terminal64.exe")) {
    Write-Fail "MT5 terminal not found at: $MT5InstallPath\terminal64.exe"
    Write-Info "Install MT5 first (Step 3 from deployment guide)."
    Stop-Transcript
    exit 1
}
Write-Ok "MT5 terminal found: $MT5InstallPath\terminal64.exe"

# Validate IP format
if ($LinuxMachineIP -notmatch '^(\d{1,3}\.){3}\d{1,3}$') {
    Write-Fail "Invalid IP address format: $LinuxMachineIP"
    Stop-Transcript
    exit 1
}
Write-Ok "Linux machine IP: $LinuxMachineIP"
Write-Ok "ZeroMQ port: $ZmqPort"

# Define key paths
$mql5Include = Join-Path $MT5DataFolder "MQL5\Include"
$mql5Libraries = Join-Path $MT5DataFolder "MQL5\Libraries"
$mql5Experts = Join-Path $MT5DataFolder "MQL5\Experts"

# Ensure directories exist
foreach ($dir in @($mql5Include, $mql5Libraries, $mql5Experts)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# ---------------------------------------------------------------------------
# Step 2: Windows Hardening
# ---------------------------------------------------------------------------
Write-Step "Step 2: Windows Hardening"

# 2.4 Configure firewall for ZeroMQ
Write-Info "Configuring Windows Firewall..."
$existingRule = Get-NetFirewallRule -DisplayName "eTradie ZeroMQ EA*" -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Info "Removing existing firewall rule..."
    Remove-NetFirewallRule -DisplayName "eTradie ZeroMQ EA*"
}

New-NetFirewallRule `
    -DisplayName "eTradie ZeroMQ EA (port $ZmqPort)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $ZmqPort `
    -RemoteAddress $LinuxMachineIP `
    -Action Allow `
    -Profile Any `
    -Description "Allow ZeroMQ connections from eTradie Linux server only. Created by setup_vps.ps1" | Out-Null
Write-Ok "Firewall rule created: port $ZmqPort open for $LinuxMachineIP only"

# 2.6 Disable unnecessary services
Write-Info "Disabling unnecessary services..."
$servicesToDisable = @(
    @{ Name = "Spooler"; Desc = "Print Spooler" },
    @{ Name = "WSearch"; Desc = "Windows Search" }
)
foreach ($svc in $servicesToDisable) {
    $s = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($s -and $s.Status -eq "Running") {
        Stop-Service -Name $svc.Name -Force -ErrorAction SilentlyContinue
        Set-Service -Name $svc.Name -StartupType Disabled
        Write-Ok "Disabled: $($svc.Desc) ($($svc.Name))"
    } elseif ($s) {
        Set-Service -Name $svc.Name -StartupType Disabled
        Write-Ok "Already stopped, disabled startup: $($svc.Desc)"
    } else {
        Write-Info "Service not found (OK): $($svc.Name)"
    }
}

# 2.7 Set timezone to UTC
Write-Info "Setting timezone to UTC..."
Set-TimeZone -Id "UTC"
Write-Ok "Timezone set to UTC"

# ---------------------------------------------------------------------------
# Step 4: Install ZeroMQ EA Dependencies
# ---------------------------------------------------------------------------
Write-Step "Step 4: Installing ZeroMQ EA Dependencies"

$tempDir = Join-Path $env:TEMP "etradie_setup"
if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

# 4.1 Install mql-zmq
Write-Info "Downloading mql-zmq..."
$zmqZip = Join-Path $tempDir "mql-zmq.zip"
Invoke-WebRequest `
    -Uri "https://github.com/dingmaotu/mql-zmq/archive/refs/heads/master.zip" `
    -OutFile $zmqZip
Write-Ok "Downloaded mql-zmq"

Write-Info "Extracting mql-zmq..."
$zmqExtract = Join-Path $tempDir "mql-zmq"
Expand-Archive -Path $zmqZip -DestinationPath $zmqExtract -Force
$zmqRoot = Join-Path $zmqExtract "mql-zmq-master"

# Copy Include/Zmq
Copy-Item -Path (Join-Path $zmqRoot "Include\Zmq") `
    -Destination (Join-Path $mql5Include "Zmq") -Recurse -Force
Write-Ok "Copied Zmq includes"

# Copy Include/Mql (required by mql-zmq)
if (Test-Path (Join-Path $zmqRoot "Include\Mql")) {
    Copy-Item -Path (Join-Path $zmqRoot "Include\Mql") `
        -Destination (Join-Path $mql5Include "Mql") -Recurse -Force
    Write-Ok "Copied Mql includes"
}

# Copy libzmq.dll (64-bit for MT5)
$dllSource = Join-Path $zmqRoot "Library\MT5\libzmq.dll"
if (-not (Test-Path $dllSource)) {
    # Some versions have different paths
    $dllSource = Get-ChildItem -Path $zmqRoot -Recurse -Filter "libzmq.dll" |
        Where-Object { $_.FullName -match "MT5|x64|64" } |
        Select-Object -First 1 -ExpandProperty FullName
}
if ($dllSource -and (Test-Path $dllSource)) {
    Copy-Item -Path $dllSource -Destination (Join-Path $mql5Libraries "libzmq.dll") -Force
    Write-Ok "Copied libzmq.dll to Libraries"
} else {
    Write-Fail "libzmq.dll not found in mql-zmq package"
    Write-Info "You may need to download it manually from the mql-zmq releases."
}

# 4.2 Install JAson
Write-Info "Downloading JAson.mqh..."
$jasonDest = Join-Path $mql5Include "JAson.mqh"
try {
    Invoke-WebRequest `
        -Uri "https://raw.githubusercontent.com/nicholishen/JAson-mql5/master/Include/JAson.mqh" `
        -OutFile $jasonDest
    Write-Ok "Downloaded JAson.mqh"
} catch {
    # Fallback URL
    try {
        Invoke-WebRequest `
            -Uri "https://raw.githubusercontent.com/nicholishen/JAson-mql5/main/Include/JAson.mqh" `
            -OutFile $jasonDest
        Write-Ok "Downloaded JAson.mqh (fallback URL)"
    } catch {
        Write-Fail "Failed to download JAson.mqh: $_"
        Write-Info "Download manually from https://github.com/nicholishen/JAson-mql5"
    }
}

# 4.3 Verify dependencies
Write-Info "Verifying dependencies..."
$requiredFiles = @(
    @{ Path = (Join-Path $mql5Include "Zmq\Zmq.mqh"); Name = "Zmq.mqh" },
    @{ Path = (Join-Path $mql5Include "JAson.mqh"); Name = "JAson.mqh" },
    @{ Path = (Join-Path $mql5Libraries "libzmq.dll"); Name = "libzmq.dll" }
)
$allDepsOk = $true
foreach ($f in $requiredFiles) {
    if (Test-Path $f.Path) {
        Write-Ok "$($f.Name) installed"
    } else {
        Write-Fail "$($f.Name) MISSING at $($f.Path)"
        $allDepsOk = $false
    }
}
if (-not $allDepsOk) {
    Write-Fail "Some dependencies are missing. Fix before continuing."
    Stop-Transcript
    exit 1
}

# Cleanup temp
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# Step 5: Deploy the ZeroMQ EA
# ---------------------------------------------------------------------------
Write-Step "Step 5: Deploying ZeroMQ EA"

$eaDest = Join-Path $mql5Experts "ZeroMQ_EA.mq5"

if ($EASourcePath -and (Test-Path $EASourcePath)) {
    Copy-Item -Path $EASourcePath -Destination $eaDest -Force
    Write-Ok "EA copied from: $EASourcePath"
} else {
    Write-Info "EA source not provided. You must copy ZeroMQ_EA.mq5 manually."
    Write-Info "Source: src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5 in the repo"
    Write-Info "Destination: $eaDest"
    if (-not (Test-Path $eaDest)) {
        Write-Warn "EA file not found at destination. Copy it before attaching to chart."
    } else {
        Write-Ok "EA file already exists at destination"
    }
}

# ---------------------------------------------------------------------------
# Step 7: MT5 Auto-Start on Reboot
# ---------------------------------------------------------------------------
Write-Step "Step 7: Configuring MT5 Auto-Start"

# 7.1 Create startup shortcut
Write-Info "Creating startup shortcut..."
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "MetaTrader5.lnk"
$mt5Exe = Join-Path $MT5InstallPath "terminal64.exe"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $mt5Exe
$shortcut.Arguments = "/portable"
$shortcut.WorkingDirectory = $MT5InstallPath
$shortcut.Description = "eTradie MT5 Terminal - Auto-start"
$shortcut.Save()
Write-Ok "Startup shortcut created: $shortcutPath"

# 7.2 Configure auto-login
Write-Info "Configuring auto-login..."
$regPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $regPath -Name "AutoAdminLogon" -Value "1"
Set-ItemProperty -Path $regPath -Name "DefaultUserName" -Value "Administrator"
Set-ItemProperty -Path $regPath -Name "DefaultPassword" -Value $VPSPassword
Write-Ok "Auto-login configured for Administrator"

# 7.3 Prevent screen lock and sleep
Write-Info "Disabling screen lock and sleep..."
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveActive" -Value "0"
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaverIsSecure" -Value "0"

# Set High Performance power plan
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
Write-Ok "Screen lock disabled, High Performance power plan active"

# Configure Windows Update active hours to prevent auto-restart during trading
Write-Info "Configuring Windows Update active hours..."
$wuPath = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
if (-not (Test-Path $wuPath)) {
    New-Item -Path $wuPath -Force | Out-Null
}
Set-ItemProperty -Path $wuPath -Name "ActiveHoursStart" -Value 0
Set-ItemProperty -Path $wuPath -Name "ActiveHoursEnd" -Value 23
Write-Ok "Windows Update active hours set to 0-23 (prevents auto-restart)"

# ---------------------------------------------------------------------------
# Post-Setup Verification
# ---------------------------------------------------------------------------
Write-Step "Post-Setup Verification"

$checks = @(
    @{ Name = "MT5 terminal executable"; Ok = (Test-Path $mt5Exe) },
    @{ Name = "ZeroMQ EA file"; Ok = (Test-Path $eaDest) },
    @{ Name = "Zmq.mqh include"; Ok = (Test-Path (Join-Path $mql5Include "Zmq\Zmq.mqh")) },
    @{ Name = "JAson.mqh include"; Ok = (Test-Path (Join-Path $mql5Include "JAson.mqh")) },
    @{ Name = "libzmq.dll library"; Ok = (Test-Path (Join-Path $mql5Libraries "libzmq.dll")) },
    @{ Name = "Startup shortcut"; Ok = (Test-Path $shortcutPath) },
    @{ Name = "Firewall rule"; Ok = ($null -ne (Get-NetFirewallRule -DisplayName "eTradie ZeroMQ EA*" -ErrorAction SilentlyContinue)) },
    @{ Name = "Timezone is UTC"; Ok = ((Get-TimeZone).Id -eq "UTC") }
)

$passed = 0
$failed = 0
foreach ($check in $checks) {
    if ($check.Ok) {
        Write-Ok $check.Name
        $passed++
    } else {
        Write-Fail $check.Name
        $failed++
    }
}

Write-Host ""
if ($failed -eq 0) {
    Write-Host "  All $passed checks passed!" -ForegroundColor Green
} else {
    Write-Host "  $passed passed, $failed failed" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Next Steps
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete - Next Steps" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "1. Launch MT5 and log into your broker account"
Write-Info "2. Enable: Tools > Options > Expert Advisors > Allow algorithmic trading"
Write-Info "3. Enable: Tools > Options > Expert Advisors > Allow DLL imports"
Write-Info "4. Compile EA: Open MetaEditor (F4) > Open ZeroMQ_EA.mq5 > Compile (F7)"
Write-Info "5. Attach EA to any chart and configure parameters (see deployment guide)"
Write-Info "6. Save chart as default template: Right-click > Templates > Save > default.tpl"
Write-Info "7. Test reboot: Restart-Computer -Force (then verify EA auto-starts)"
Write-Info "8. From Linux machine: Create VPS connection via dashboard API"
Write-Host ""
Write-Info "Log file saved to: $logFile"
Write-Host ""

Stop-Transcript
