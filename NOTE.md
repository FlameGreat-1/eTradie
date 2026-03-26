# Trade Management (Module C) Implementation Plan & Audit


## Architectural Rationale: The Necessity of Websocket Polling

We decisively adopted an Event-Driven Execution approach over a Static Time-Based (Cron) Approach. Here is the exact examination of why the original codebase was fatally flawed for a live environment, and why the current planned approach (Execution Monitoring + Gateway Polling) is the absolute **Enterprise-Grade Gold Standard.**

### The Problem with the Original Approach (Waiting for 100% Confirmation)
Imagine your TA Engine is scheduled to run every 4 hours (e.g., 04:00, 08:00, 12:00). 
- At 08:00, the TA scan runs. A beautiful Daily setup has formed, and the M15 structure (CHoCH + OB) is perfectly set up. 
- However, the live price is still 10 pips away from the Order Block (RTO hasn't happened). The original code returned `None` and hid this masterpiece from the system.
- At 09:15, the London session opens and price violently spikes into the Order Block, perfectly validating the trade!
- But your next TA scan doesn't run until 12:00! By 12:00, the trade has already hit Take Profit and finished. **You missed the trade completely.**

### Why Our Planned Approach is Enterprise Grade
Institutions do not rely on cron-job intervals to catch precise 1-minute entries. By passing "Pending" candidates from the TA Engine, we separate **Geometric Analysis** (which can run every 4 hours) from **Execution Triggering** (which must be monitored via live millisecond ticks).

- **For a Limit Order:** Execution takes the Pending Candidate at 08:00 and literally places a pending Limit Order at the broker (`entry_price`). The broker's matching engine fills it at 09:15 automatically.
- **For an Instant Order:** Execution watches the live tick feed, waits for the 09:15 touch of the POI, triggers the Gateway for a final TA safety check (Session Timing / News), and fires a Market Order in milliseconds.

This is the only way to build a professional, latency-sensitive trading system.

## Proposed Changes

We will create a completely new service under `src/management` alongside matching `.proto` files in `proto/management/`.

### 1. End-to-End Enterprise Architectural Flow

To ensure complete separation of concerns and maintain a scalable API Gateway / Orchestrator pattern, the entire enterprise system follows this strict linear sequence for every single trade setup:

**Step 1: Parallel Intelligence Collection (TA + Macro)**
- The **Gateway** initiates the cycle by collecting data from the **TA Engine** and **Macro Engine** simultaneously via parallel goroutines.
- TA produces the precise price patterns, SMC/SnD candidates, and structural metrics.
- Macro produces fundamental data, events, and COT positioning.

**Step 2: RAG Retrieval & Context Assembly**
- The **Gateway** filters the TA results for active candidates. For each candidate, it combines the TA snapshot and Macro data to dynamically build a precise context query.
- It hits the **RAG Engine** (the rulebook Brain), which returns a bundle of specific framework rules and historical parameters.
- The **Gateway** then merges all three outputs (TA + Macro + RAG Bundle) into a master context object.

**Step 3: Processor LLM Analysis**
- The **Gateway** feeds this assembled master context directly to the **Processor (LLM)**.
- The Processor evaluates confluence against the rules and returns an analyzed `Trade Thesis` (Action, Grade, Confidence) back to the Gateway.

**Step 4: Execution Handoff (Gateway → Execution)**
- The **Gateway** passes the accepted thesis through its routing guards. If approved, it delegates execution to the **Execution Service (Module B)**.
- **Gateway Override Capability:** The Gateway can dynamically override the user's default execution mode (e.g., forcing INSTANT instead of LIMIT) based on real-time market volatility or LLM thesis. The Execution service honours this `ExecutionMode` override.

**Step 5: Trade Execution (Gateway → Execution)**
- The **Execution Service (Module B)** takes 100% complete ownership of getting the trade filled at the broker. It handles both order types natively based on how confirmations are treated:
  - **LIMIT Order (Risk Entry):** The TA Engine detected the HTF pattern and verified the setup geometry. Execution immediately places a pending Limit Order at the exact determined point (Fibonacci/OB level) directly into the broker and waits for it to be hit naturally.
  - **INSTANT Order (Confirmation Entry - The Polling Loop):** 
    1. **Pre-Confirmed Fast Path:** If the initial TA analysis arrives with `ltf_confirmation=True` (meaning the setup and LTF confirmation had already fully formed prior to the 4H scan), Execution bypasses the polling loop completely and fires the market order immediately. *(Note: The Gateway is designed to correctly extract nested `ltf_confirmation` maps from the TA Engine JSON payload).*
    2. **Pending Setup Path:** If the initial TA analysis arrives with `ltf_confirmation=False`:
       a. Execution spawns a background goroutine and monitors the live tick feed.
       b. It waits for the price to drop into the setup's **POI (Point of Interest)** — which could be an Order Block for SMC or a Supply/Demand Zone for SnD.
       c. The exact millisecond price touches the POI, Execution signals the Gateway: *"Price is in the zone! Start checking for confirmation."*
       d. The **Gateway initiates a Polling Loop**: It calls the TA Engine exactly **every 5 minutes** (running standard 1W-M1 analysis, without Macro or RAG). **Cache Bypass:** This confirmation pulse explicitly bypasses the Gateway's Redis cache to guarantee a fresh TA analysis every time.
       e. Gateway checks the TA output. If the TA successfully finds the setup with `ltf_confirmation=True`, Gateway tells Execution to fire the market order natively.
       f. **Database Write:** The TA Engine automatically persists snapshots and candidates on every fresh analysis triggered by the cache-bypassed confirmation pulse, ensuring LTF confirmations are recorded.
       g. If the pattern is not confirmed after **45 minutes** (timeout), the Gateway aborts the loop and signals Execution to drop the setup entirely.

**Step 6: Execution Confirmation & Handoff (Execution → Gateway)**
- The instant the trade is officially executed and **FILLED** at the broker, the **Execution Service** immediately signals back to the **Gateway**: *"Execution complete. The trade is filled."*

**Step 7: Post-Fill Trade Management (Gateway → Module C)**
- The **Gateway** completes the orchestration sequence by calling the **Trade Management Engine (Module C)**. It hands over the live position saying: *"A trade was just confirmed executed. Here is the open position, entry, SL, and TP levels. Take over."*
- From this millisecond forward, **Module C** owns the trade (Trail stops, BE, partial closes, End-of-Day closures).









When the Gateway (Module A) analyzes the market and decides to take a trade, there are two possible scenarios for an **INSTANT** order:

**Scenario A: The setup is forming, but not fully confirmed yet.**
*   The HTF (Higher Timeframe) setup exists (e.g., M15 Order Block).
*   However, the LTF (Lower Timeframe) confirmation (e.g., M1 change of character) *has not happened yet*.
*   **What happens:** The Gateway sends the trade to Execution with `LTFConfirmed = false`. The Execution Service starts the **Watcher**, monitors the live tick price, waits for price to enter the zone, and sets up a polling loop to keep asking the Gateway, *"Is it confirmed yet? How about now?"*

**Scenario B: The setup is ALREADY perfectly confirmed right now.**
*   When the Gateway runs its analysis, it sees that *both* the HTF setup exists *and* the LTF confirmation has already occurred on the chart at that very second!
*   **What happens (The Fast Path):** There is absolutely no reason for the Execution Service to start a Watcher, poll prices, or ask the Gateway for confirmation again. The Gateway already knows it is confirmed!
*   So, the Gateway sends the trade to Execution with `LTFConfirmed = true`.
*   The Execution Service sees this flag, says *"Ah, this is already confirmed!"*, completely skips the entire Watcher monitoring phase, and **instantly fires the market order to the broker.** This guarantees blazing fast execution and zero latency for setups that are already ripe.

-
**The actual execution of LIMIT vs INSTANT modes is natively handled by the Execution Service (Module B).** 
- Execution is the engine that actually places the Limit Order or starts the live tick Watcher.
- Module C (Trade Management) has been completely removed from the pre-execution phase.

**However, the *decision* of which mode to use is now controlled by both:**
By default, the Execution Service reads your preferred setting from the database (e.g., you set your whole system to trade via Limit orders). 

But, I added a powerful override feature for the Gateway. Because the Gateway houses the AI Processor, it might analyze a specific trade and realize: *"This market is too volatile right now. Even though the user's default is LIMIT, this specific trade MUST be executed instantly to guarantee a fill."* 
- The Gateway can now pass `ExecutionMode: "INSTANT"` in its payload for that specific trade. 
- The Execution Service will honour the Gateway's override for that one trade.

**Summary:** The Execution Service (Module B) does 100% of the heavy lifting (placing orders, watching ticks, calling for confirmation), but the Gateway (Module A) now has the power to dictate the mode and tell Execution when a trade is already "pre-confirmed" to save time.


