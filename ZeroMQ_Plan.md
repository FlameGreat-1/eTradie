# Enterprise Hybrid MT5 Architecture Plan (100% Decoupled)

This architecture establishes a **Universal Platform Support** system. We are completely migrating from the official `MetaTrader5` Python library to a ZeroMQ-based system. This ensures the application runs natively on **macOS**, **Linux**, and **Windows** without ever crashing.

## The Hybrid Concept
We will use Two Network-based Providers:

### 1. Cloud Provider (`metaapi`)
- **Environment**: Linux VPS (Railway, Contabo) or macOS.
- **Bridge**: MetaApi.cloud REST/Websocket API.
- **Status**: 24/7 Production. No local terminal or laptop required.

### 2. Native Provider (`native`)
- **Environment**: Your local machine (Windows, **macOS, or Linux**).
- **Communication**: ZeroMQ Network Socket.
- **Bridge**: **ZeroMQ Expert Advisor (`ZeroMQ_EA.mq5`)** running on a Windows PC (yours or a friend's).
- **Security Check (PING)**: In Native Mode, the Engine will **NOT** store or send credentials to the EA. You log in to your Exness account manually in the MT5 Terminal. The Engine only sends a `PING` command to confirm the bridge is active.
- **Docker Connectivity**: We will add `extra_hosts` to the `docker-compose.yml` to ensure the Linux container can resolve `host.docker.internal` to the `host-gateway`.
- **Status**: On-demand testing/trading. A Mac user can run the Engine on their Mac and connect it to a Windows PC on the same network. No Cloud required.

---

## Technical Execution Plan

### Step 1: Configuration Refactoring
Update `src/engine/ta/broker/mt5/config.py`:
- `provider: Literal["metaapi", "native"]`
- `zmq_host`, `zmq_port` (Set this to the IP of the Windows PC running MT5)
- `metaapi_token`, `metaapi_account_id` (For cloud MetaApi mode)

### Step 2: Implementation (No more `import MetaTrader5`)
1. **`metaapi/client.py`**: Communicates with MetaApi cloud servers.
2. **`zmq/client.py`**: Communicates with the local ZeroMQ EA bridge on your chart.

### Step 3: Domain Registry Update
We will update `src/engine/ta/broker/registry.py` to act as a factory. When the Engine starts, it will check the `provider` setting and instantiate the correct implementation based on the `MT5_PROVIDER` env variable.

---

## 🌍 Why this is better
*   **macOS & Linux Users:** Can now run the eTradie Engine natively. They simply use the `metaapi` provider. They don't need to install MetaTrader 5 on their computers at all.
*   **Windows Users:** Can choose between `metaapi` (Cloud) or `native` (ZeroMQ Bridge).
*   **Zero Platform Crashes**: Since we have deleted the Windows-only `MetaTrader5` library, the `etradie-engine` will now build and run on any operating system perfectly.