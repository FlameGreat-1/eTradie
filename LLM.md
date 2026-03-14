The LLM is the **judge**.

The Macro pipeline and TA pipeline are just data collectors. They find things — structures, zones, bias signals, COT numbers, DXY direction. They do not know if any of it means anything together.

The RAG retrieves rules and examples. But rules sitting in a prompt are not a decision.

**The LLM's job is to look at all of it simultaneously and answer one question:**

> *Does this specific combination of macro environment + market structure + zone quality + confluence factors constitute a valid, high-probability setup according to the rules — and if yes, exactly where do you enter, where does the thesis break, and what are the targets?*

That is something neither the TA engine nor the RAG can do alone. The TA engine sees a 4H OB. It does not know if that OB is tradeable right now. The RAG knows the rules for what makes an OB tradeable. But it cannot look at the live data and apply those rules. The LLM holds both simultaneously and reasons across them.

More specifically, the LLM does five things:

**1. Cross-framework synthesis**
It reads the 4H OB from TA, the supply zone from SnD, the DXY direction from macro, the COT positioning, the Wyckoff phase — and determines whether they are all pointing at the same thing or contradicting each other. No individual pipeline can see across all six frameworks at once. The LLM can.

**2. Conflict resolution**
If the 4H is bullish but the 1D macro is bearish — the TA engine cannot resolve that. The RAG rule says conflicting timeframes = NO SETUP. The LLM reads both, matches the conflict to the rule, and outputs NO SETUP. This is judgment applied to structured inputs.

**3. Confluence scoring**
It counts how many of the 10 confluence factors are genuinely present in the live data — not assumed, not partially present. It assigns the score and grade. A scoring algorithm could count fields but cannot determine whether a liquidity sweep actually swept the relevant SSL or just touched a random level. The LLM reads the TA output and the SMC rule and makes that determination.

**4. Trade construction**
If the setup is valid — it calculates the precise entry zone (OTE 62–79% of OB), places the SL beyond the structural invalidation level, identifies the three TP targets from the liquidity pools and structural levels in the TA output, and calculates the R:R. This requires understanding the geometry of the setup, not just filling fields.

**5. Evidence chain**
It produces a reasoning chain that cites the specific RAG rule or scenario that justifies every decision. This is what prevents hallucination — every claim in the output traces back to a retrieved document chunk. If it cannot cite a rule, it cannot make the claim.

---

In one sentence: **the LLM turns structured data + retrieved rules into a reasoned, evidence-backed trade decision that no individual component in the pipeline is capable of producing alone.**



Exact Module A Analysis Output schema Processor must produce (the canonical output)

The LLM output must be transformed/validated into this JSON structure (this exact fieldset is required by Rulebook & TechSpec — every field must be present). Use these field names and types exactly:


THIS IS JUST AN EXAMPLE. WE CAN HAVE SOMETHING BETTER AND POWERFUL:

{
  "analysis_id": "string",
  "pair": "EURUSD",
  "timestamp": "2026-03-02T09:14:32Z",
  "trading_style": "INTRADAY",
  "session": "LONDON_OPEN",

  "macro_bias": {
    "base_currency": {"bias": "BULLISH", "evidence": ["rule_id", "quote", "chunk_id"]},
    "quote_currency": {"bias": "BEARISH", "evidence": [...]}
  },

  "dxy_bias": {
    "direction": "BEARISH",
    "evidence": [{"doc_id":"master_rulebook_v1","section":"DXY rules","chunk_id":"..."}]
  },

  "cot_signal": {
    "summary":"net speculative long increasing",
    "week_over_week":"increase",
    "extreme_flag": false,
    "evidence":[ ... ]
  },

  "event_risk": [
    {"event":"NFP","time":"2026-03-05T13:30:00Z","impact":"HIGH"}
  ],

  "1w_bias": {"structure":"bullish","notes":"HH HL formation"},
  "1d_bias": {"structure":"choch_bullish","key_levels":[/* price levels */]},
  "4h_setup": {"type":"OB","zone_id":"OB_20260302_01","quality":"A","bounds":[1.0832,1.0850]},

  "wyckoff_phase": {"phase":"markup","evidence":[ ... ]},

  "confluence_score": {"score": 8.5, "factors": [{"name":"DXY alignment","value":1},{"name":"1D BOS","value":2}, ...]},

  "setup_grade": "A+",            // A+ / A / B / REJECT
  "direction": "LONG",            // LONG / SHORT / NO SETUP

  "entry_zone": {"low":1.08320,"high":1.08500},

  "stop_loss": {"price":1.07780,"reason":"below OB low + 3 pip buffer","evidence":[ ... ]},

  "take_profits":[
    {"level":1.09200,"size_pct":40,"basis":"nearest liquidity pool"},
    {"level":1.09850,"size_pct":30,"basis":"1D structure"},
    {"level":1.10500,"size_pct":30,"basis":"1W drive"}
  ],

  "rr_ratio": 5.38,
  "confidence":"HIGH",           // HIGH / MEDIUM / LOW / NO SETUP

  "rag_sources": [
    {"doc_id":"smc_framework_v1","chunk_id":"c_023","section":"Order Block validity"}
  ],

  "proceed_to_module_b":"YES",   // YES / NO
  "explainable_reasoning":"string (human readable reasoning summary)",

  "audit": {
    "retrieval": {
       "query": {/* the retrieval query used */},
       "top_k": 8,
       "chunks_returned":[ /* chunk ids and scores */ ]
    },
    "citations":[ /* document/chunk -> rule mapping listed here */ ]
  }
}


Important: this JSON must always be fully populated even when direction: "NO SETUP" — in that case many fields will be null or explicitly "NO SETUP" but the keys must exist (Rulebook mandates non-negotiable output shape).



THIS IS JUST AN EXAMPLE, WE SHOULD HAVE SOMETHING BETTER:


9 — Citation & audit logging (exact fields to persist)

Every successful or NO-SETUP analysis must write a row to rag_retrieval_logs and analysis_audit_log in Postgres with:

analysis_id, pair, timestamp

retrieval_query (json)

retrieval_results (list of chunk summaries & scores)

coverage: boolean + details

conflicts: boolean + details

llm_request: hashed prompt reference id (do not store raw prompt text unless needed) — store prompt_id mapping to prompt template + variables in rag_prompts table

llm_response: the JSON emitted by LLM

citations: list of {doc_id, chunk_id, section, doc_version}

final_decision: proceed_to_module_b yes/no, grade, confidence

verifications: results of post-LLM validation checks

This audit trail is required by the Rulebook (versioning & citation requirements).