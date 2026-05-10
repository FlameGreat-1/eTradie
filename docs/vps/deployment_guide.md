# MT4/MT5 Auto-Provisioning Deployment Guide

> Production deployment guide for the headless MetaTrader 4 and 5 integration.
>
> The eTradie platform automatically spins up containerized MetaTrader terminals natively within your Kubernetes (K3s) cluster. **You do NOT need a dedicated Windows VPS.**

---

## 1. Cloud-Agnostic Architecture

The eTradie Engine dynamically provisions broker instances on-demand using the `kubernetes_asyncio` library. When a user connects a broker account via the dashboard, the Engine spawns a dedicated pod running the custom `etradie-mt-node` Docker image.

```text
┌────────────────────────────────────────────────────────┐
│ Kubernetes Cluster (K3s)                               │
│                                                        │
│  ┌─────────────────┐       ┌───────────────────────┐   │
│  │ eTradie Engine  │       │ etradie-mt-node Pod   │   │
│  │ (Python)        ├──────►│ (Headless Wine/Xvfb)  │   │
│  │                 │ ZMQ   │                       │   │
│  └──────┬──────────┘       │ ┌───────────────────┐ │   │
│         │                  │ │ MT4 / MT5         │ │   │
│         ▼ API              │ │ + ZeroMQ_EA       │ │   │
│  ┌─────────────────┐       │ └───────────────────┘ │   │
│  │ Kubernetes API  │◄──────┤                       │   │
│  └─────────────────┘       └───────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

### Key Advantages
1. **No Windows Server Required**: Completely eliminates the need for expensive Windows VPS licenses.
2. **Headless Execution**: Uses `Xvfb` (X Virtual Framebuffer) and Wine to run the Windows GUI terminals completely headlessly.
3. **High Security**: The ZeroMQ port (5555) is only exposed internally within the Kubernetes cluster, preventing external internet attacks.
4. **Instant Scalability**: Handles dozens of independent MT4/MT5 accounts by spinning up isolated pods for each connection.

---

## 2. The `etradie-mt-node` Docker Image

The custom MetaTrader container acts as the backbone of the auto-provisioning system.

### Build Process
Before deployment, you must bake your compiled `.ex4` and `.ex5` ZeroMQ Expert Advisors into the image.

1. Compile the MT4 EA (`ZeroMQ_EA.ex4`) and MT5 EA (`ZeroMQ_EA.ex5`) using MetaEditor on your local PC.
2. Place them in `docker/mt-node/ea/`.
3. Build the image:
```bash
make build-mt-node
make push-mt-node
```

### Dynamic Startup Injection
When the Pod boots up, the `entrypoint.sh` script executes the following sequence:
1. Detects the requested platform via the `MT_PLATFORM` environment variable (`mt4` or `mt5`).
2. Copies the corresponding binary (`terminal.exe` vs `terminal64.exe`) and EA (`.ex4` vs `.ex5`).
3. Generates a custom `startup.ini` config on the fly, injecting the user's `MT_LOGIN`, `MT_PASSWORD`, and `MT_SERVER`.
4. Starts `Xvfb` on Display :99 and launches the MetaTrader terminal natively in Wine.

---

## 3. Connecting via the Dashboard

Because the system manages the infrastructure, connecting a broker account is fully automated.

1. Go to **My Broker** in the dashboard.
2. Select **MetaTrader 4** or **MetaTrader 5**.
3. Enter your account credentials (Login, Password, Server).
4. Click **Connect**.

Behind the scenes:
- The Engine contacts the Kubernetes API and requests a new Pod.
- The Pod pulls the `etradie-mt-node` image and injects your credentials.
- The MetaTrader terminal launches, authenticates with the broker, and attaches the ZeroMQ EA.
- The Engine verifies the ZMQ connection via an internal cluster IP address.

---

## 4. Legacy Windows PC Connection (Fallback)

If you prefer to run the EA on your local Windows PC for testing or debugging, the system still supports the legacy `native` mode over the public internet or local network.

### Steps for Local Connection:
1. Ensure your local PC's port `5555` is open in Windows Firewall to allow the Engine to connect.
2. Open MetaTrader 4/5 on your local PC and manually attach the `ZeroMQ_EA`.
3. Configure the `AUTH_TOKEN` in the EA settings.
4. In the dashboard, choose **Custom EA Connection**, provide your local PC's IP address, and the exact same Auth Token.

> **SECURITY WARNING:** If you use this fallback over the public internet, ensure your Windows Firewall strictly whitelists the IP address of your Linux server. ZeroMQ traffic is unencrypted in transit.