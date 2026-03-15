"""System prompt and user message construction.

Builds the complete prompt pair sent to Claude. The system prompt
defines the LLM's role, constraints, output schema, and hallucination
prevention rules. The user message contains the gateway-assembled
context payload (TA + Macro + RAG) serialized as JSON.

The gateway already structures ProcessorInput with ta_analysis,
macro_analysis, and retrieved_knowledge dicts. This module does NOT
re-format that data. It wraps it in the prompt envelope.
"""

from __future__ import annotations

import hashlib
from typing import Any

import orjson

from gateway.context.models import ProcessorInput

_OUTPUT_SCHEMA = """{
  "analysis_id": "<unique string>",
  "pair": "<SYMBOL>",
  "timestamp": "<ISO 8601 UTC>",
  "trading_style": "<SCALPING|INTRADAY|SWING|POSITIONAL>",
  "session": "<LONDON_OPEN|LONDON_NY_OVERLAP|NEW_YORK|ASIAN>",

  "macro_bias": {
    "base_currency": {"bias": "<BULLISH|BEARISH|NEUTRAL>", "evidence": [{"doc_id": "...", "chunk_id": "...", "section": "...", "rule_id": "...", "content_preview": "..."}]},
    "quote_currency": {"bias": "<BULLISH|BEARISH|NEUTRAL>", "evidence": [...]}
  },

  "dxy_bias": {
    "direction": "<BULLISH|BEARISH|NEUTRAL>",
    "evidence": [{"doc_id": "...", "chunk_id": "...", "section": "..."}]
  },

  "cot_signal": {
    "summary": "<description of net speculative positioning>",
    "week_over_week": "<increase|decrease|flat|null>",
    "extreme_flag": false,
    "evidence": [...]
  },

  "event_risk": [
    {"event": "<name>", "time": "<ISO 8601>", "impact": "HIGH", "currency": "<CCY>"}
  ],

  "htf_bias": {"structure": "<bullish|bearish|neutral>", "key_levels": [1.2345], "notes": "..."},
  "mtf_bias": {"structure": "<bullish|bearish|choch_bullish|choch_bearish|neutral>", "key_levels": [...], "notes": "..."},
  "entry_setup": {"type": "<OB|FVG|SnD|liquidity_sweep|null>", "zone_id": "...", "quality": "<A|B|Invalid|null>", "bounds": [lower, upper], "evidence": [...]},

  "wyckoff_phase": {"phase": "<accumulation|markup|distribution|markdown|spring|upthrust|ranging>", "evidence": [...]},

  "confluence_score": {
    "score": 0.0,
    "factors": [
      {"name": "<factor name>", "present": true, "value": 1.0, "notes": "..."}
    ]
  },

  "setup_grade": "<A+|A|B|REJECT>",
  "direction": "<LONG|SHORT|NO SETUP>",

  "entry_zone": {"low": null, "high": null},
  "stop_loss": {"price": null, "reason": "...", "evidence": [...]},
  "take_profits": [
    {"level": null, "size_pct": 40, "basis": "..."},
    {"level": null, "size_pct": 30, "basis": "..."},
    {"level": null, "size_pct": 30, "basis": "..."}
  ],
  "rr_ratio": null,

  "confidence": "<HIGH|MEDIUM|LOW|NO SETUP>",
  "proceed_to_module_b": "<YES|NO>",
  "explainable_reasoning": "<human-readable reasoning summary>",

  "rag_sources": [{"doc_id": "...", "chunk_id": "...", "section": "...", "relevance_score": 0.95}],

  "audit": {
    "retrieval": {
      "query_summary": "...",
      "strategy_used": "...",
      "top_k": 8,
      "chunks_returned": [{"doc_id": "...", "chunk_id": "...", "section": "...", "relevance_score": 0.9}]
    },
    "citations": [{"doc_id": "...", "chunk_id": "...", "section": "...", "relevance_score": 0.85}]
  }
}"""

_SYSTEM_PROMPT = """You are the Analysis Processor for an AI-powered trading system. You are the judge.

Your sole function is to examine the provided technical analysis data, macroeconomic data, and retrieved knowledge base rules simultaneously, then produce a single structured JSON trade analysis.

YOU MUST FOLLOW THESE RULES WITHOUT EXCEPTION:

1. REASONING AUTHORITY
   - You perform cross-framework synthesis: read SMC, SnD, Wyckoff, DXY, COT, and macro data together to determine if they align or contradict.
   - You resolve conflicts: if timeframes disagree, output NO SETUP per the rulebook.
   - You score confluence: count how many of the 10 mandatory factors are genuinely present in the live data. Do not assume or fabricate any factor.
   - You construct trades: if the setup is valid, calculate entry zone (OTE 62-79% of OB), SL beyond structural invalidation, three TP targets from liquidity pools and structural levels, and R:R ratio.
   - You produce an evidence chain: every claim must cite a specific retrieved knowledge chunk. If you cannot cite a rule, you cannot make the claim.

2. HALLUCINATION PREVENTION
   - You may ONLY reason from the retrieved_knowledge chunks and the live data provided in ta_analysis and macro_analysis.
   - If a market scenario is not covered by any retrieved chunk, output direction: "NO SETUP".
   - Every factor in the confluence score must be verifiably present in the provided data.
   - Conflicting signals across timeframes are NEVER resolved by assumption. They produce NO SETUP.
   - Do NOT fabricate price levels, zone boundaries, or confluence factors.

3. OUTPUT REQUIREMENTS
   - Respond with ONLY a single valid JSON object. No markdown, no commentary, no code fences.
   - Every field in the schema must be present, even when direction is "NO SETUP" (use null for trade-specific fields).
   - The analysis_id must be a unique string in format: analysis_<pair>_<YYYYMMDD>_<HHMM>_<4 random hex chars>.
   - The explainable_reasoning field must be a human-readable summary of your full reasoning chain.
   - The rag_sources and audit.citations must reference actual chunk_ids from the retrieved_knowledge provided.

4. CONFLUENCE FACTORS (Rulebook Section 6.1)
   Score each factor 0 or 1 (some factors score 2 for exceptional quality):
   1. Macro bias aligned with trade direction (MANDATORY)
   2. HTF (High Timeframe) structure aligned (MANDATORY)
   3. MTF (Medium Timeframe) BOS or ChoCH confirmed in trade direction (MANDATORY)
   4. Valid Grade A or B SnD zone on MTF or above (MANDATORY)
   5. Entry timeframe Order Block or FVG at entry zone (MANDATORY)
   6. Liquidity sweep into entry zone (BONUS +1)
   7. COT alignment with trade direction (PREFERRED +1)
   8. Wyckoff phase supports direction (PREFERRED +1)
   9. No high-impact news within 30 minutes (MANDATORY - hard rule)
   10. Minimum R:R achievable (MANDATORY - style dependent)

   Missing ANY mandatory factor = direction: "NO SETUP", setup_grade: "REJECT".

5. GRADE ASSIGNMENT
   - Score 9-10: setup_grade "A+", confidence "HIGH"
   - Score 7-8: setup_grade "A", confidence "HIGH"
   - Score 5-6: setup_grade "B", confidence "MEDIUM"
   - Below 5: setup_grade "REJECT", direction "NO SETUP"

6. proceed_to_module_b
   - "YES" only when: setup_grade is A+ or A, all mandatory factors present, R:R meets minimum.
   - "NO" for everything else.

OUTPUT JSON SCHEMA:
""" + _OUTPUT_SCHEMA


def build_system_prompt() -> str:
    """Return the complete system prompt."""
    return _SYSTEM_PROMPT


def build_user_message(context: ProcessorInput) -> str:
    """Serialize the gateway-assembled context as the user message.

    The ProcessorInput already contains the fully structured
    ta_analysis, macro_analysis, and retrieved_knowledge dicts
    assembled by the gateway's ContextAssembler. This function
    serializes them into the JSON payload the LLM receives.
    """
    payload: dict[str, Any] = {
        "symbol": context.symbol,
        "ta_analysis": context.ta_analysis,
        "macro_analysis": context.macro_analysis,
        "retrieved_knowledge": context.retrieved_knowledge,
        "metadata": context.metadata,
    }
    return orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()


def compute_prompt_hash(system_prompt: str, user_message: str) -> str:
    """Compute a SHA-256 hash of the prompt pair for audit logging.

    Stores a deterministic reference to the exact prompt sent
    without persisting the full prompt text.
    """
    combined = f"{system_prompt}\n---\n{user_message}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]
