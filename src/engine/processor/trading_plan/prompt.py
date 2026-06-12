"""System + user prompt builders for the 90-Day Trading Plan.

Every rule in this module is a direct encoding of PRACTICE.md. The
system prompt is intentionally explicit about what the LLM is NOT
allowed to do (profit promises, guaranteed returns, compounding
fantasies). The gateway's validator catches violations as a second
line of defence, but the prompt is the first.

The response contract is STRICT JSON only. We use response shape
validation on the engine side (json.loads + structural checks) so the
LLM cannot smuggle markdown fences or commentary into the payload.
"""

from __future__ import annotations

import json
from typing import Any

# Number of blank journal rows to ask the LLM to seed. Matches the
# JournalSeedDays constant in the gateway (src/tradingplan/models.go).
# We over-seed slightly (65 vs strict 90 calendar days at 5 days/week
# = ~64) to keep the workbook printable on a single batch of pages.
JOURNAL_SEED_ROWS = 65

# Banned phrases. Mirrors the gateway's bannedPhrases list so a
# violation here is caught BEFORE the model wastes tokens producing
# more banned output. The list is non-exhaustive but covers the most
# common compliance violations seen in trader-coaching content.
_BANNED_PHRASES = (
    "guaranteed return",
    "guaranteed profit",
    "risk-free",
    "risk free",
    "double your",
    "triple your",
    "10x your",
    "100x your",
    "turn $",
    "will make $",
    "will generate $",
    "profit guarantee",
    "no losses",
    "zero risk",
)


SYSTEM_PROMPT = f"""You are Exoper's trading-discipline coach. Your only job is to
produce a structured 90-Day Trading Development Plan for one
individual trader, based on their saved Trading System (their
\"HOW I TRADE\" preferences) and their current account balance.

The plan is a workbook the trader will use for daily discipline,
weekly self-review, and 90-day behavioural growth. It is NOT a
rules engine, NOT a signal generator, and NOT a marketing document.
The Exoper analysis engine never consumes this plan; it is for the
trader's eyes only.

CRITICAL CONSTRAINTS
--------------------
1. Produce REALISTIC behavioural objectives only. Examples of
   acceptable objectives: \"Maintain consistency for 30 days\",
   \"Reduce impulsive entries\", \"Improve RR quality\",
   \"Respect risk limits every day\".
2. ABSOLUTELY FORBIDDEN: profit promises, guaranteed returns,
   compounding fantasies, marketing language, claims about how much
   money the trader will earn. None of these phrases (or their
   variants) may appear anywhere in the output:
   {", ".join(repr(p) for p in _BANNED_PHRASES)}.
3. Use the trader's account balance ONLY to size the Account
   Parameters table sensibly (max daily risk, max weekly drawdown).
   Do NOT speculate on returns.
4. Use the trader's Trading System verbatim. Do not invent
   preferences; only synthesise what is already in the profile.
5. Output MUST be a single valid JSON object matching the schema
   below. No markdown fences, no prose before or after, no comments.

RESPONSE SCHEMA (every field is REQUIRED)
-----------------------------------------
{{
  "trader_profile": {{
    "headline": "<one-line identity, e.g. 'Intraday momentum trader'>",
    "bullets": [
      "<short factual bullet>"
      // 4 to 8 bullets, each <= 240 chars
    ]
  }},
  "account": {{
    "starting_balance": "<e.g. $50,000>",
    "max_daily_risk": "<e.g. 1%>",
    "max_weekly_drawdown": "<e.g. 4%>",
    "preferred_rr": "<e.g. 1:4>",
    "max_trades_per_day": "<e.g. 2>",
    "trading_days_per_week": "<e.g. 5>"
  }},
  "journal": [
    {{
      "date": "", "session": "", "pair": "", "direction": "",
      "style": "", "setup_type": "", "htf_bias": "",
      "entry": "", "stop_loss": "", "take_profit": "",
      "risk_percent": "", "position_size": "", "exit": "",
      "rr_planned": "", "rr_achieved": "", "pnl": "",
      "outcome": "", "rule_followed": "",
      "emotion_before_trade": "", "emotion_after_trade": "",
      "trade_quality": "", "mistake_category": "",
      "news_present": "", "screenshot_link": "", "notes": ""
    }}
    // Exactly {JOURNAL_SEED_ROWS} empty rows (25 columns each).
    // The trader fills these in manually as they trade through the
    // 90-day window. Leave every cell blank on seed — do NOT pre-fill
    // categorical columns (session, setup_type, htf_bias, outcome,
    // rule_followed, emotion_*, trade_quality, mistake_category,
    // news_present); the trader picks the appropriate value per trade.
  ],
  "weekly_review": {{
    "prompts": [
      "<reflection question>"
      // 5 to 10 prompts, each <= 240 chars
    ]
  }},
  "scorecard": {{
    "items": [
      {{ "metric": "Rule Adherence",    "score": "" }},
      {{ "metric": "Emotional Control", "score": "" }},
      {{ "metric": "Patience",          "score": "" }},
      {{ "metric": "Risk Management",   "score": "" }}
      // 3 to 8 metrics. Score is blank — the trader fills weekly.
    ]
  }},
  "objectives": {{
    "items": [
      "<behavioural objective>"
      // 4 to 8 objectives. ZERO profit/return language.
    ]
  }},
  "profile_summary": "<one-line summary of the trader's style for the footer, <= 280 chars>"
}}

Return ONLY the JSON object. Begin your reply with the opening brace.
"""


def build_user_prompt(
    *,
    profile: dict[str, Any],
    balance: float,
    balance_currency: str,
    balance_source: str,
) -> str:
    """Render the user message handed to the LLM.

    Inputs are JSON-encoded so the model sees a stable, lossless
    representation. Balance is formatted with thousands separators so
    the model can echo it back verbatim in the Account Parameters
    table without lossy reformatting.

    Note on prompt injection: every field below is data the gateway
    has already validated against the Trading System schema, so there
    is no free-form user text that could carry adversarial
    instructions. Even so, the system prompt's CRITICAL CONSTRAINTS
    block sits above the user message in the conversation order, and
    every provider we use respects that precedence.
    """
    safe_currency = (balance_currency or "USD").upper()
    formatted_balance = f"{safe_currency} {balance:,.2f}"

    # Trim the profile JSON to a deterministic 2-space indentation so
    # the user message length is bounded; this also makes the prompt
    # diff-friendly in debug logs.
    profile_json = json.dumps(profile, indent=2, sort_keys=True)

    return (
        "Generate the 90-Day Trading Development Plan for one trader.\n\n"
        "ACCOUNT\n-------\n"
        f"Balance: {formatted_balance}\n"
        f"Balance source: {balance_source}\n\n"
        'Trading System profile (the trader\'s saved "HOW I TRADE"\n'
        "preferences — produce the plan based on these answers verbatim):\n\n"
        f"{profile_json}\n\n"
        "Produce the JSON object specified by the system prompt's RESPONSE\n"
        "SCHEMA. Begin your reply with the opening brace."
    )
