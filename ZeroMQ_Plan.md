# Enterprise MT5 ZeroMQ Expert Advisor (EA) Architecture Plan

This document outlines the exact execution steps for **Enterprise Solution 1: ZeroMQ Expert Advisor**. We are completely abandoning the "Python hack" and building a true, industry-standard decoupled execution bridge using pure MQL5 and ZeroMQ (ZMQ).

## The Core Concept
Your `etradie-engine` (running securely inside a Linux Docker container) will act purely as a client. It will send lightweight JSON commands (like "GET_CANDLES" or "EXECUTE_TRADE") over a raw TCP socket directly to an Expert Advisor (EA) that you attach to a chart on your Windows MT5 terminal. 

The EA natively operates within the MT5 C++ environment, securely executing the commands and returning the results back over the TCP socket.

---

## Execution Phases

### Phase 1: The Windows MT5 Expert Advisor (MQL5)
The engine cannot interact directly with MetaTrader5 natively anymore. Instead, we must compile a permanent Expert Advisor designed solely as a router.
1. We will establish the industry-standard **Darwinex ZeroMQ Connector (`DWX_ZeroMQ_Connector`)** protocol, or build a custom lightweight MQL5 EA with `libzmq.dll` attached.
2. The EA will continuously run on a single chart in your Windows MT5 terminal.
3. The EA will securely bind two local TCP ports (e.g., `5555` for Commands/Requests, `5556` for asynchronous Price Pub/Sub).
4. The EA will precisely parse JSON payloads from the Engine, execute them natively (e.g. `CopyRates`), serialize the result, and echo it back to the Engine.

### Phase 2: Refactoring the Linux Docker Engine
We must entirely rewrite your Engine's MT5 Broker layer to operate exclusively over ZeroMQ.

#### 1. Add ZeroMQ to the Engine
- Add `pyzmq` (Python ZeroMQ wrapper) and `msgpack` dependencies to the `etradie-engine` requirements.

#### 2. Rewrite `mt5/config.py`
- Remove native MT5 credential configs (the EA handles login natively on its host).
- Add `zmq_req_port`, `zmq_sub_port`, and `host` (defaulting to `host.docker.internal`).

#### 3. Rewrite `mt5/client.py`
- Remove all traces of `import MetaTrader5`.
- Instantiate a persistent `zmq.Context()` and connect the `REQ` and `SUB` sockets to the EA's IP.
- Rewrite `fetch_candles()`:
  * From: `rates = mt5.copy_rates_from(...)`
  * To: `payload = {"action": "GET_RATES", "symbol": symbol, "timeframe": tf}; socket.send_json(payload); response = socket.recv_json();`
- Rewrite `health_check()` to just send a tiny ping over ZMQ to verify the EA is alive and attached.

### Phase 3: The Deployment Workaround
1. **Host Configuration:** I will compile the `.mq5` EA file and securely install the required `libzmq.dll` into your Windows MT5 terminal directory.
2. **Docker Orchestration:** Your Docker containers cleanly start up on WSL Linux. The Go Gateway and Engine seamlessly communicate over Go/Python internals, while the Engine safely fires micro-orders directly out to the Windows MT5 EA.

---

## Why this is the Industry Standard
* **Decoupled Security:** The EA strictly guards execution. The Engine never needs your brokerage credentials natively configured.
* **Ultimate Scalability:** You can easily add zero-latency Pub/Sub streams from the EA up to the Engine, instantly beaming new tick ticks to your Linux infrastructure directly.
* **Cross-platform Stability:** If an MT5 update corrupts a Python backend natively (which happens violently often), we are perfectly insulated. The REST/ZMQ protocol never changes.




🛡️ Go Services Isolation (Gateway, Execution, Management)
First and foremost: There are zero changes required for your Go microservices. The Gateway and Execution services interact with the Engine's high-level API. The fact that the Engine is now talking to MT5 via ZeroMQ instead of a native library is completely hidden from them. The BrokerBase interface in the Engine remains stable, so the Go services will continue to work perfectly without any modifications.

🛠️ Exact Files to be Updated (Engine Only)
The migration is surgically limited to the following 4 files within the Engine:

1. requirements/base.txt: We will add pyzmq and msgpack so the Linux container has the necessary networking tools.

2. src/engine/ta/broker/mt5/config.py: We'll add the connection settings for the Windows host (e.g., zmq_host, zmq_port).

3. src/engine/ta/broker/mt5/client.py: This is where the "brain" of the communication lives. We will replace the Windows-only MetaTrader5 calls with efficient ZeroMQ request/response logic.

4. src/engine/ta/broker/mt5/__init__.py: We'll remove the temporary "safe mock" I added earlier, as it's no longer needed once the real ZMQ client is in place.


The application will use your login, 

password
, and 

server
 exactly like it does now. Here is how it stays automated:

The Engine (in Linux) still holds your credentials in its 

.env
 file.
When the Engine starts, it sends a "LOGIN" command over the ZeroMQ connection to the Expert Advisor on Windows.
The Expert Advisor receives your login, 

password
, and 

server
, and it immediately tells the MT5 Terminal to log in to that account.
The Engine waits for a "Success" reply from the EA, and then continues its trading tasks.
The result is exactly the same as before: The system logs in automatically without you needing to manually type anything into the MT5 terminal.