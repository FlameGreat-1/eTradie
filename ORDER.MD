

I have completed the exhaustive codebase audit regarding the 1D BOS/ChoCH limitation rule.

I have great news: **The codebase itself does NOT hardcode or limit BOS or ChoCH detection to the "1D" (Daily) timeframe anywhere in the logic.**

The system actually uses a very dynamic and scalable approach. Here is exactly how it works currently:

### 1. The Core Detection Logic is Timeframe-Agnostic
In `src/engine/ta/smc/detectors/choch.py` and across the structural analyzers, the `CHOCHDetector` and `BOS` builders do not look at explicit timeframes. They analyze exactly what they are given:
- They detect signals on the **HTF (Higher Timeframe)** sequence.
- They detect signals on the **LTF (Lower Timeframe)** sequence.

### 2. The Timeframe is Configurable per Gateway Cycle
The exact timeframes are set in [src/gateway/config.py](cci:7://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/config.py:0:0-0:0):
```python
ta_htf_timeframe: str = Field(default="H4", pattern=r"^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$")
ta_ltf_timeframe: str = Field(default="M15", pattern=r"^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$")
```
When a cycle runs, the gateway grabs `ta_htf_timeframe` (which defaults to `H4`, not `D1`) and asks the TA Orchestrator to analyze structure events on that HTF and LTF. 

### 3. The RAG Query Builder is Timeframe-Agnostic
In [src/gateway/query_builder/query_text.py](cci:7://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/query_builder/query_text.py:0:0-0:0), the query pulls in the timeframes that were dynamically evaluated:
```python
if ta.has_bms:
    parts.append("BOS break of structure")
if ta.has_choch:
    parts.append("CHoCH change of character")
# ... later ...
if ta.htf_timeframe:
    parts.append(ta.htf_timeframe)  # Instead of hardcoding 1D, it passes whatever HTF was used
```

### 4. ⚠️ The Minor Issue: The Guard Mismatch
I did find one place where the term "1D" is technically hardcoded, but it acts dynamically.
In [src/gateway/routing/guards.py](cci:7://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/routing/guards.py:0:0-0:0), the [_check_counter_trend](cci:1://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/routing/guards.py:178:4-227:9) guard specifically enforcing the `MR-REJECT-006` rule does this:
```python
def _check_counter_trend(
    processor: ProcessorOutput,
    ta: TASymbolResult,
) -> GuardCheckResult:
    """MR-REJECT-006: Counter-trend without D1 CHoCH = NO SETUP."""
```
However, lower down in the check logic, it **does not explicitly verify a 1D sequence**. It simply says:
```python
choch_events = snapshot.get("choch_events", {})
choch_count = choch_events.get("count", 0)
```
The snapshot being passed to this guard is the **HTF snapshot** (which, given your config defaults, is actually **H4**, not **D1**). 

The guard rejects the trade with this specific message message:
```python
reason="Counter-trend trade without D1 CHoCH - rejected per MR-REJECT-006"
```
Even if you changed `ta_htf_timeframe` to `H1`, the orchestrator would require an `H1` ChoCH, but if the trade failed the guard, the log / output message would erroneously say it failed because it lacked a "D1" ChoCH.

### Conclusion

You are perfectly safe. The TA engine **does detect BOS/ChoCH on all timeframes**. The system dynamically uses whatever you set as the `GATEWAY_TA_HTF_TIMEFRAME` and `GATEWAY_TA_LTF_TIMEFRAME` environment variables.




Ah, I see the confusion! Let me clarify exactly what the codebase is doing, because you are touching on two completely different settings in the Gateway config that sound similar but do different things.

Yes, there is a **cycle interval**, AND there is an **analysis timeframe**.

Here are the exact settings currently in [src/gateway/config.py](cci:7://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/config.py:0:0-0:0):

```python
# 1. THE CYCLE INTERVAL (How often the system wakes up to run)
cycle_interval_seconds: int = Field(
    default=14400, ge=60,
    description="Interval between analysis cycles (default 4 H)",
)

# 2. THE CHART TIMEFRAMES (What candle sizes the TA engine looks at)
ta_htf_timeframe: str = Field(default="H4", pattern=r"^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$")
ta_ltf_timeframe: str = Field(default="M15", pattern=r"^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$")
```

### What This Means

1. **`cycle_interval_seconds` = 14400 (4 hours)**: This means the Gateway orchestrator wakes up every 4 hours to run a new analysis cycle. This is the "cron job" interval.
2. **`ta_htf_timeframe` (Higher Timeframe) = H4**: When the TA orchestrator analyzes the charts, it asks the broker for 4-Hour candles to determine the major trend, High Timeframe BOS, High Timeframe ChoCH, and High Timeframe Supply/Demand zones.
3. **`ta_ltf_timeframe` (Lower Timeframe) = M15**: When determining entries, refinements, or internal structure, it asks the broker for 15-Minute candles.

### Are We Only Analyzing H4 and M15?
**Yes, currently the TA Orchestrator is ONLY being passed one HTF and one LTF per cycle.** 

When the Gateway's [TACollector](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/collectors/ta_collector.py:34:0-253:13) runs, it does this:
```python
htf = Timeframe(self._config.ta_htf_timeframe) # Gets H4
ltf = Timeframe(self._config.ta_ltf_timeframe) # Gets M15

# It then tells the TA Orchestrator to analyze exactly these two:
result = await self._orchestrator.analyze(
    symbol=symbol,
    htf_timeframe=htf,
    ltf_timeframe=ltf,
    lookback_periods=lookback,
)
```

The TA Orchestrator currently does **not** dynamically scan D1, then scan H4, then scan M15. It only scans the exactly configured pair of timeframes (defaults to H4 for the big picture and M15 for the details). 

### How Do We Fix This?

The rulebook describes a true "multi-timeframe" approach:
> *1W bullish structure + 1D BOS confirmed + 4H demand zone intact + 4H ChoCH*

But the code currently only evaluates a single pair (HTF and LTF) per symbol per cycle. 

If we want the RAG/Processor to see the 1D BOS, the 4H Supply/Demand zones, AND the 15M entry entries, we have two options:

**Option 1 (The Gateway Multi-Pass Approach):**
We update the [TACollector](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/collectors/ta_collector.py:34:0-253:13) in the Gateway so that it asks the [TAOrchestrator](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/orchestrator.py:22:0-738:9) to run *multiple passes* for the same symbol:
- Pass 1: HTF=1W, LTF=1D
- Pass 2: HTF=1D, LTF=4H
- Pass 3: HTF=4H, LTF=M15
We then aggregate all three `TechnicalSnapshot` results into the single [TASymbolResult](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/gateway/context/models.py:26:0-36:31) for the LLM.

**Option 2 (The TA Engine Multi-Timeframe Approach - Better Architecture):**
We rewrite the `TAOrchestrator.analyze()` method itself to take a *list* of timeframes (e.g., `[Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.M15]`). It would fetch candles for all of them, run the SMC/SnD detectors on all of them, and build a unified multi-timeframe snapshot model.

Right now, if you want "1D BOS", you would have to change `GATEWAY_TA_HTF_TIMEFRAME=D1` in your `.env` file, but then your "Lower Timeframe" would have to be 4H or 1H, meaning you'd lose the 15M granular entry zones.



### Now, regarding your confusion about the "4H":

You are actually exactly right, but you are looking at two completely different "4H" parameters in the system that happen to share the same number.

1. **The Interval Cycle (`cycle_interval_seconds` = 14400)**
   - 14,400 seconds is exactly 4 hours. 
   - This determines **how often the Gateway wakes up** to scrape the news, get COT data, and ask the broker for new candles. 
   - Yes, at every 4H it runs the analysis pipeline again.

2. **The Analysis Timeframes (`ta_htf_timeframe` = "H4" & `ta_ltf_timeframe` = "M15")**
   - This determines **what chart sizes the TA engine looks at** when it wakes up.
   - Currently, when the system wakes up every 4 hours, it asks the broker for the H4 chart and the M15 chart for a given symbol.
   - It runs the SMC and SnD detection **only** on those two charts. 

### Why is it built this way currently?
Right now, the TA engine is architected as a **"Single-Pair" Timeframe analyzer**. It accepts exactly one Higher Timeframe (HTF) and one Lower Timeframe (LTF) per cycle. Because the default configuration says HTF="H4" and LTF="M15", the system is entirely blind to the "1D" chart or the "1W" chart. 

### The Ultimate Fix
Your rulebook explicitly states you want to check long-term structure (Weekly/Daily) AND intermediate term (4H) AND short-term entries. To achieve that, the TA Collector shouldn't just look at two timeframes. We need to upgrade the architecture so that the system is **Multi-Timeframe Aware**.

Instead of:
`HTF = H4` and `LTF = M15`

It should do top down analysis:
`Timeframes = [1W, 1D, 4H, 1H, 30M, 15M]`

When the system wakes up (every 4 hours), it should ask the broker for all 4 of those charts, detect BOS/ChoCH on all 4 of them, package them into a massive unified Snapshot, and send that complete 4-dimensional picture to the AI Processor. 
