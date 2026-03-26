# MT5 + ZeroMQ EA: Contabo Windows VPS Deployment Guide

> Production deployment guide for running MetaTrader 5 with the eTradie
> ZeroMQ Expert Advisor on a Contabo Windows Server VPS for 24/7 trading.
>
> The eTradie Docker stack (engine, gateway, execution, management, etc.)
> stays on the existing Linux machine. Only MT5 + EA moves to the VPS.
> The local Windows PC is kept as backup.

---

## Architecture

```
┌─────────────────────────────────┐
│   Linux Machine (Unchanged)     │
│   ┌─────────────────────────┐   │
│   │  eTradie Docker Stack   │   │
│   │  engine:8000            │   │
│   │  gateway:8080           │   │
│   │  execution:50053        │   │
│   │  management:50054       │   │
│   │  postgres, redis, etc.  │   │
│   └──────────┬──────────────┘   │
│              │ ZMQ (tcp)        │
└──────────────┼──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Contabo Windows VPS (NEW)      │
│  Public IP: <VPS_IP>            │
│  ┌─────────────────────────┐    │
│  │  MT5 Terminal            │   │
│  │  + ZeroMQ EA             │   │
│  │  Listening: 0.0.0.0:5555 │   │
│  └─────────────────────────┘    │
│  Firewall: port 5555 open       │
│  for Linux machine IP only      │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  Local Windows PC (BACKUP)      │
│  IP: 192.168.43.183:5555        │
│  MT5 + ZeroMQ EA (unchanged)    │
│  Switch back anytime via        │
│  dashboard connection activate  │
└─────────────────────────────────┘
```

---

## Prerequisites

- Contabo account (https://contabo.com)
- Credit card or PayPal for VPS payment
- MT5 broker account credentials (login, password, server)
- The eTradie Linux machine must have a static public IP or a way
  to determine its outbound IP (for firewall whitelisting)
- RDP client on your local machine (Windows: built-in, Mac: Microsoft
  Remote Desktop, Linux: Remmina or xfreerdp)

---

## Step 1: Order Contabo Windows VPS

### 1.1 Go to Contabo VPS page

https://contabo.com/en/vps/

### 1.2 Select VPS plan

**Recommended minimum for MT5 + ZeroMQ EA:**

| Spec | Minimum | Recommended |
|---|---|---|
| CPU | 4 vCPU | 6 vCPU |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB SSD | 100 GB NVMe |
| OS | Windows Server 2022 | Windows Server 2022 |
| Location | Closest to your broker's server | EU or US depending on broker |

**Contabo plan: VPS M or VPS L** (approximately $10-25/month + Windows license ~$5/month)

### 1.3 Configuration options

- **Operating System:** Windows Server 2022 Standard
- **Region:** Choose closest to your MT5 broker server
  - If broker is in London: choose EU (Germany or UK)
  - If broker is in New York: choose US East
- **Networking:** Standard (public IPv4 included)
- **Backup:** Optional but recommended ($2-3/month)

### 1.4 Complete order

After payment, Contabo provisions the VPS within 1-24 hours.
You receive an email with:
- VPS public IP address
- Administrator username (usually `Administrator`)
- Administrator password
- RDP port (usually 3389)

**Save these credentials securely. You will need them for every step below.**

---

## Step 2: Initial VPS Setup

### 2.1 Connect via RDP

```
IP: <VPS_IP>
Port: 3389
Username: Administrator
Password: <from Contabo email>
```

### 2.2 Change Administrator password

First thing after login. Open PowerShell as Administrator:

```powershell
net user Administrator "YourNewStrongPassword123!"
```

### 2.3 Run Windows Update

Settings > Windows Update > Check for updates > Install all > Restart

Repeat until no more updates are available. This is critical for security.

### 2.4 Configure Windows Firewall for ZeroMQ

Open PowerShell as Administrator:

```powershell
# Create firewall rule allowing ZeroMQ connections ONLY from your Linux machine.
# Replace <LINUX_MACHINE_IP> with the public IP of your Linux server.

New-NetFirewallRule `
    -DisplayName "eTradie ZeroMQ EA (port 5555)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5555 `
    -RemoteAddress <LINUX_MACHINE_IP> `
    -Action Allow `
    -Profile Any `
    -Description "Allow ZeroMQ connections from eTradie Linux server only"
```

**CRITICAL SECURITY:** Do NOT use `-RemoteAddress Any`. Only whitelist
your Linux machine's IP. ZeroMQ has no built-in encryption; restricting
by IP is the primary network-level protection.

If your Linux machine's IP changes, update the rule:

```powershell
Set-NetFirewallRule `
    -DisplayName "eTradie ZeroMQ EA (port 5555)" `
    -RemoteAddress <NEW_LINUX_IP>
```

### 2.5 Verify firewall rule

```powershell
Get-NetFirewallRule -DisplayName "eTradie ZeroMQ EA*" | Format-List
```

### 2.6 Disable unnecessary services

```powershell
# Disable Print Spooler (not needed, common attack vector)
Stop-Service -Name Spooler -Force
Set-Service -Name Spooler -StartupType Disabled

# Disable Windows Search (saves resources)
Stop-Service -Name WSearch -Force
Set-Service -Name WSearch -StartupType Disabled
```

### 2.7 Set timezone to UTC

MT5 server times are typically UTC or UTC+2/+3. Set the VPS to UTC
to avoid confusion:

```powershell
Set-TimeZone -Id "UTC"
```

---

## Step 3: Install MT5 Terminal

### 3.1 Download MT5

Open Edge browser on the VPS and download MT5 from your broker's website,
or from the official MetaTrader site:

https://www.metatrader5.com/en/download

### 3.2 Install MT5

- Run the installer
- Install to: `C:\Program Files\MetaTrader 5` (default)
- Complete the installation
- **Do NOT launch MT5 yet** (we need to install EA dependencies first)

### 3.3 Locate MT5 data folder

The MT5 data folder is where EAs, includes, and libraries are stored.
It is NOT the installation folder. To find it:

1. Launch MT5 briefly
2. Go to File > Open Data Folder
3. Note the path (typically `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\<HASH>`)
4. Close MT5

We will refer to this as `<MT5_DATA_FOLDER>` in the steps below.

---

## Step 4: Install ZeroMQ EA Dependencies

The EA requires two libraries that must be installed manually.

### 4.1 Install mql-zmq (ZeroMQ for MQL5)

Source: https://github.com/dingmaotu/mql-zmq

```powershell
# Download mql-zmq
Invoke-WebRequest `
    -Uri "https://github.com/dingmaotu/mql-zmq/archive/refs/heads/master.zip" `
    -OutFile "$env:TEMP\mql-zmq.zip"

# Extract
Expand-Archive -Path "$env:TEMP\mql-zmq.zip" -DestinationPath "$env:TEMP\mql-zmq" -Force

# Copy Include files
$dataFolder = "<MT5_DATA_FOLDER>"  # Replace with actual path
Copy-Item -Path "$env:TEMP\mql-zmq\mql-zmq-master\Include\Zmq" `
    -Destination "$dataFolder\MQL5\Include\Zmq" -Recurse -Force
Copy-Item -Path "$env:TEMP\mql-zmq\mql-zmq-master\Include\Mql" `
    -Destination "$dataFolder\MQL5\Include\Mql" -Recurse -Force

# Copy DLL (64-bit)
Copy-Item -Path "$env:TEMP\mql-zmq\mql-zmq-master\Library\MT5\libzmq.dll" `
    -Destination "$dataFolder\MQL5\Libraries\libzmq.dll" -Force

Write-Host "mql-zmq installed successfully" -ForegroundColor Green
```

### 4.2 Install JAson (JSON parser for MQL5)

Source: https://github.com/nicholishen/JAson-mql5

```powershell
# Download JAson
Invoke-WebRequest `
    -Uri "https://raw.githubusercontent.com/nicholishen/JAson-mql5/master/Include/JAson.mqh" `
    -OutFile "$dataFolder\MQL5\Include\JAson.mqh"

Write-Host "JAson.mqh installed successfully" -ForegroundColor Green
```

### 4.3 Verify dependencies

```powershell
# Check all required files exist
$files = @(
    "$dataFolder\MQL5\Include\Zmq\Zmq.mqh",
    "$dataFolder\MQL5\Include\JAson.mqh",
    "$dataFolder\MQL5\Libraries\libzmq.dll"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  OK: $f" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $f" -ForegroundColor Red
    }
}
```

---

## Step 5: Deploy the ZeroMQ EA

### 5.1 Copy the EA file

The EA source is in the repository at:
`src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5`

Copy this file to the VPS:

```powershell
# Option A: Copy from your local machine via RDP clipboard
# Open the file on your local machine, copy contents, paste into
# a new file on the VPS at:
# <MT5_DATA_FOLDER>\MQL5\Experts\ZeroMQ_EA.mq5

# Option B: Download directly from GitLab (if repo is accessible)
# Invoke-WebRequest -Uri "<GITLAB_RAW_URL>" -OutFile "$dataFolder\MQL5\Experts\ZeroMQ_EA.mq5"
```

### 5.2 Compile the EA

1. Launch MT5
2. Open MetaEditor (F4 or Tools > MetaQuotes Language Editor)
3. Open `MQL5\Experts\ZeroMQ_EA.mq5`
4. Click Compile (F7)
5. Verify: 0 errors in the output panel
6. Close MetaEditor

If compilation fails, check that all dependencies from Step 4 are in
the correct folders.

---

## Step 6: Configure MT5 and Attach EA

### 6.1 Log into your broker account

1. In MT5: File > Login to Trade Account
2. Enter your broker credentials:
   - Login: your account number
   - Password: your trading password
   - Server: your broker's server (e.g. ICMarketsSC-Demo)
3. Click OK
4. Verify connection: bottom-right status bar should show connection speed

### 6.2 Enable algorithmic trading

1. Tools > Options > Expert Advisors tab
2. Check: "Allow algorithmic trading"
3. Check: "Allow DLL imports" (required for ZeroMQ)
4. Click OK

### 6.3 Attach EA to a chart

1. Open any chart (the symbol does not matter; the EA works globally)
   - Recommended: open a chart of your most-traded pair (e.g. EURUSD)
2. In the Navigator panel (Ctrl+N), expand Expert Advisors
3. Drag "ZeroMQ_EA" onto the chart
4. In the EA settings dialog:

**Network Configuration:**
| Parameter | Value | Notes |
|---|---|---|
| ZMQ_PORT | 5555 | Must match firewall rule |
| RECV_TIMEOUT_MS | 1000 | Default is fine |
| SEND_TIMEOUT_MS | 5000 | Default is fine |

**Security:**
| Parameter | Value | Notes |
|---|---|---|
| AUTH_TOKEN | `<your-secure-token>` | Generate a strong random string (32+ chars). This MUST match what you enter in the dashboard EA setup. |

**Trading Configuration:**
| Parameter | Value | Notes |
|---|---|---|
| MAGIC_NUMBER | 20260321 | Default. Change if running multiple EAs. |
| MAX_SLIPPAGE | 10 | Points. Adjust for your broker. |
| MAX_LOT_SIZE | 10.0 | Maximum per order. Adjust to your risk. |
| MAX_TOTAL_EXPOSURE | 50.0 | Total lots across all positions. |
| MAX_DRAWDOWN_PCT | 20.0 | Blocks new trades if exceeded. |

**Performance:**
| Parameter | Value | Notes |
|---|---|---|
| TIMER_MS | 50 | 20 polls/sec. Default is fine. |

**Logging:**
| Parameter | Value | Notes |
|---|---|---|
| ENABLE_DEBUG_LOG | false | Set true only for troubleshooting |
| LOG_COMMANDS | true | Recommended for production audit trail |

5. Click OK
6. Verify: the EA should show a smiley face on the chart
7. Check the Experts tab (Ctrl+T, Experts tab) for:
   ```
   [INFO] [ZMQ_EA] === eTradie ZeroMQ Bridge Started ===
   [INFO] [ZMQ_EA] Endpoint: tcp://*:5555
   [INFO] [ZMQ_EA] Ready for commands
   ```

### 6.4 Save as template for auto-attach

This ensures the EA re-attaches automatically when MT5 restarts:

1. Right-click on the chart > Templates > Save Template
2. Save as: `default.tpl`
3. When prompted to overwrite, click Yes

Now whenever MT5 opens, it loads the default template which includes
the EA with all your configured parameters.

---

## Step 7: Set Up MT5 Auto-Start on Reboot

The VPS may reboot for Windows updates or maintenance. MT5 must
start automatically.

### 7.1 Create a startup shortcut

```powershell
# Create shortcut in Windows Startup folder
$startupFolder = [Environment]::GetFolderPath('Startup')
$mt5Path = "C:\Program Files\MetaTrader 5\terminal64.exe"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut("$startupFolder\MetaTrader5.lnk")
$shortcut.TargetPath = $mt5Path
$shortcut.Arguments = "/portable"  # Use portable mode for consistent data folder
$shortcut.WorkingDirectory = "C:\Program Files\MetaTrader 5"
$shortcut.Description = "eTradie MT5 Terminal"
$shortcut.Save()

Write-Host "MT5 auto-start shortcut created at: $startupFolder\MetaTrader5.lnk" -ForegroundColor Green
```

### 7.2 Configure auto-login for the VPS

MT5 requires a desktop session to run (it is a GUI application).
The VPS must auto-login after reboot:

```powershell
# Enable auto-login for Administrator
$regPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $regPath -Name "AutoAdminLogon" -Value "1"
Set-ItemProperty -Path $regPath -Name "DefaultUserName" -Value "Administrator"
Set-ItemProperty -Path $regPath -Name "DefaultPassword" -Value "<YOUR_VPS_PASSWORD>"

Write-Host "Auto-login configured for Administrator" -ForegroundColor Green
```

**SECURITY NOTE:** Auto-login stores the password in the registry.
This is acceptable for a dedicated trading VPS that only runs MT5.
Do NOT use this on a shared or multi-purpose server.

### 7.3 Prevent screen lock

MT5 may stop processing if the screen locks:

```powershell
# Disable screen saver and lock screen
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveActive" -Value "0"
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaverIsSecure" -Value "0"

# Set power plan to High Performance (never sleep)
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

Write-Host "Screen lock and sleep disabled" -ForegroundColor Green
```

### 7.4 Test auto-start

1. Restart the VPS: `Restart-Computer -Force`
2. Wait 2-3 minutes
3. Connect via RDP
4. Verify MT5 is running with the EA attached
5. Check the Experts tab for the startup messages

---

## Step 8: Verify from Linux Machine

On your Linux machine where the eTradie Docker stack runs:

### 8.1 Test ZeroMQ connectivity

```bash
# From the eTradie project directory
docker compose exec engine python scripts/zmq_test.py \
    --mode ping
```

But first, you need to temporarily set the ZMQ host to the VPS IP.
The easiest way is to use the dashboard:

### 8.2 Create VPS EA connection via dashboard

Call the API (or use the dashboard UI when available):

```bash
curl -X POST http://localhost:8000/api/broker/connections \
  -H "Content-Type: application/json" \
  -d '{
    "connection_type": "ea",
    "name": "VPS EA - Contabo",
    "ea_host": "<VPS_PUBLIC_IP>",
    "ea_port": 5555,
    "ea_auth_token": "<same-token-as-EA-AUTH_TOKEN>",
    "mt5_server": "ICMarketsSC-Demo",
    "mt5_login": "51234567",
    "activate": true
  }'
```

### 8.3 Test the connection

```bash
# Get the connection ID from the create response
curl -X POST http://localhost:8000/api/broker/connections/<CONNECTION_ID>/test
```

Expected response:
```json
{
  "connection_id": "...",
  "healthy": true,
  "status": "connected",
  "message": "Connection successful"
}
```

### 8.4 Save local PC as backup connection

```bash
curl -X POST http://localhost:8000/api/broker/connections \
  -H "Content-Type: application/json" \
  -d '{
    "connection_type": "ea",
    "name": "Local PC Backup",
    "ea_host": "192.168.43.183",
    "ea_port": 5555,
    "ea_auth_token": "etradie_secure_token_2026",
    "mt5_server": "ICMarketsSC-Demo",
    "mt5_login": "51234567",
    "activate": false
  }'
```

Now you have two connections saved:
1. **VPS EA - Contabo** (active, primary)
2. **Local PC Backup** (inactive, ready to activate if VPS fails)

---

## Step 9: Rollback to Local PC

If the VPS has issues and you need to switch back to the local PC:

### Option A: Via Dashboard API

```bash
# List connections to find the local PC connection ID
curl http://localhost:8000/api/broker/connections

# Activate the local PC connection
curl -X POST http://localhost:8000/api/broker/connections/<LOCAL_PC_ID>/activate
```

This immediately hot-swaps the broker client. No restart needed.

### Option B: Via Environment Variables

If the dashboard is not accessible:

```bash
# Edit .env on the Linux machine
MT5_ZMQ_HOST=192.168.43.183  # Local PC IP

# Restart containers
docker compose down && docker compose up -d
```

---

## Step 10: Monitoring and Maintenance

### 10.1 Daily checks

- Verify MT5 is connected to broker (check connection status in MT5)
- Check EA Experts tab for errors
- Test connection from dashboard: `POST /api/broker/connections/<ID>/test`

### 10.2 Weekly maintenance

- Check Windows Update on VPS (schedule updates for weekends)
- Review MT5 journal for any disconnection events
- Verify auto-start still works: restart VPS and confirm EA comes back

### 10.3 Windows Update strategy

Configure Windows Update to NOT auto-restart during trading hours:

```powershell
# Set active hours (trading hours) to prevent auto-restart
# Forex market: Sunday 22:00 UTC to Friday 22:00 UTC
# Set active hours to cover the full trading week
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name "ActiveHoursStart" -Value 0
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name "ActiveHoursEnd" -Value 23
```

Manually install updates on Saturday when markets are closed.

---

## Troubleshooting

### EA shows "Not authenticated" error

- The `AUTH_TOKEN` in the EA parameters must exactly match the
  `ea_auth_token` you entered in the dashboard broker connection.
- Check for trailing spaces or invisible characters.

### Connection test returns "Health check failed"

1. **Check firewall:** Is port 5555 open for your Linux machine's IP?
   ```powershell
   # On VPS
   Get-NetFirewallRule -DisplayName "eTradie*" | Format-List
   ```

2. **Check MT5 is running:** Is the terminal open with the EA attached?
   ```powershell
   # On VPS
   Get-Process terminal64 -ErrorAction SilentlyContinue
   ```

3. **Check EA is loaded:** Look at the Experts tab in MT5 for startup messages.

4. **Check network:** From the Linux machine:
   ```bash
   # Test TCP connectivity to VPS port 5555
   nc -zv <VPS_IP> 5555
   ```

### MT5 disconnects from broker frequently

- Check VPS network stability in Contabo control panel
- Ensure the VPS is not running out of memory
- Check if Windows Update triggered a restart

### EA stops responding after VPS reboot

1. Connect via RDP
2. Check if MT5 started (look in taskbar)
3. If MT5 is running but EA is not attached:
   - The default template may not have saved correctly
   - Re-attach the EA and save the template again (Step 6.4)
4. If MT5 did not start:
   - Check the startup shortcut (Step 7.1)
   - Check auto-login is configured (Step 7.2)

### "DLL imports are not allowed" error

- Tools > Options > Expert Advisors > Check "Allow DLL imports"
- Also check the EA properties: right-click EA on chart > Properties >
  Dependencies tab > "Allow DLL imports" must be checked

---

## Security Checklist

- [ ] VPS Administrator password changed from default
- [ ] Windows Update installed (all critical updates)
- [ ] Firewall rule restricts port 5555 to Linux machine IP only
- [ ] EA AUTH_TOKEN is a strong random string (32+ characters)
- [ ] RDP access restricted (consider changing default port 3389)
- [ ] No unnecessary services running on VPS
- [ ] MT5 trading password is not the same as the VPS password
- [ ] Broker connection credentials encrypted in eTradie database

---

## Cost Summary

| Item | Monthly Cost |
|---|---|
| Contabo VPS M (4 vCPU, 8GB RAM) | ~$7-12 |
| Windows Server license | ~$5 |
| Optional backup | ~$2-3 |
| **Total** | **~$14-20/month** |

Compared to running a local PC 24/7:
- Electricity savings: ~$15-30/month
- Hardware wear reduction: extends PC lifespan
- Reliability: data center uptime vs home power/internet
- Accessibility: manage from anywhere via RDP