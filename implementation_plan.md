
---

## User Review Required
> [!IMPORTANT]
> **Enterprise Hybrid MT5 Architecture Migration**
> To support both 24/7 Cloud Trading (Railway/Contabo) and Local Development (Windows), we will implement a dual-provider Hybrid Broker.

### Phase 1: Dual-Provider Configuration
We will introduce a [provider](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/config.py#407-414) switch in the MT5 configuration.
- **Mode 1: `metaapi` (Cloud/Production)**: Uses the `metaapi-sdk` for **24/7 Linux VPS** deployment.
- **Mode 2: `native` (Local/Development)**: Uses a **ZeroMQ EA Bridge**. This allows the Engine to talk to your Windows MT5 terminal over a network socket without needing the native library.

> [!IMPORTANT]
> **This architecture COMPLETELY REMOVES the `MetaTrader5` Python library from the codebase.** 
> By using ZeroMQ for local mode and MetaApi for cloud mode, we eliminate all Windows-specific library dependencies and cross-platform crashes forever.

### Phase 2: Refactoring the Engine's MT5 Module
#### [MODIFY] [config.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/mt5/config.py)
- Add `provider: Literal["metaapi", "native"] = "metaapi"`.
- Add `zmq_host`, `zmq_port` for Native Mode.
- Add `metaapi_token`, `metaapi_account_id` for Cloud Mode.

#### [NEW] [metaapi.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/mt5/metaapi.py)
- Implementation of the cloud-native REST/Websocket bridge.

#### [NEW] [zmq_client.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/mt5/zmq_client.py)
- Implementation of the ZeroMQ request/response bridge (replaces the old native logic).

### Phase 3: Infrastructure
#### [MODIFY] [requirements/base.txt](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/requirements/base.txt)
- Add `metaapi-sdk`, `pyzmq`, and `msgpack`.
- **DELETE** `MetaTrader5` from all dependency lists.
