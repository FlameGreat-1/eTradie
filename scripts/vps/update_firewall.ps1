#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Update the ZeroMQ firewall rule with a new Linux machine IP.

.DESCRIPTION
    When the Linux machine's public IP changes (e.g., ISP reassignment,
    server migration), this script updates the Windows Firewall rule
    to allow ZeroMQ connections from the new IP only.

    The old IP is blocked immediately. Only the new IP is whitelisted.

.PARAMETER NewIP
    The new public IP address of the Linux machine.

.PARAMETER ZmqPort
    ZeroMQ port. Default: 5555.

.EXAMPLE
    .\update_firewall.ps1 -NewIP "198.51.100.42"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$NewIP,

    [int]$ZmqPort = 5555
)

$ErrorActionPreference = "Stop"
$ruleName = "eTradie ZeroMQ EA (port $ZmqPort)"

# Validate IP format
if ($NewIP -notmatch '^(\d{1,3}\.){3}\d{1,3}$') {
    Write-Host "[FAIL] Invalid IP address format: $NewIP" -ForegroundColor Red
    exit 1
}

# Validate each octet is 0-255
$octets = $NewIP.Split('.')
foreach ($octet in $octets) {
    if ([int]$octet -lt 0 -or [int]$octet -gt 255) {
        Write-Host "[FAIL] Invalid IP octet: $octet in $NewIP" -ForegroundColor Red
        exit 1
    }
}

# Check if rule exists
$rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $rule) {
    Write-Host "[FAIL] Firewall rule not found: $ruleName" -ForegroundColor Red
    Write-Host "  Run setup_vps.ps1 first to create the rule." -ForegroundColor Yellow
    exit 1
}

# Get current remote address
$currentFilter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $rule
$currentIP = $currentFilter.RemoteAddress
Write-Host "  Current allowed IP: $currentIP" -ForegroundColor White
Write-Host "  New IP:             $NewIP" -ForegroundColor White

if ($currentIP -eq $NewIP) {
    Write-Host "[INFO] IP is already set to $NewIP. No change needed." -ForegroundColor Yellow
    exit 0
}

# Update the rule
Set-NetFirewallRule -DisplayName $ruleName -RemoteAddress $NewIP

# Verify
$updatedRule = Get-NetFirewallRule -DisplayName $ruleName
$updatedFilter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $updatedRule

if ($updatedFilter.RemoteAddress -eq $NewIP) {
    Write-Host "[OK] Firewall rule updated: $currentIP -> $NewIP" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Firewall rule update may have failed. Verify manually:" -ForegroundColor Red
    Write-Host "  Get-NetFirewallRule -DisplayName '$ruleName' | Get-NetFirewallAddressFilter" -ForegroundColor Gray
    exit 1
}
