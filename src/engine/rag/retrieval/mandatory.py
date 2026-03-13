"""Mandatory retrieval rules engine.

Determines which knowledge chunks MUST be present in every retrieval
result regardless of semantic similarity scores. This prevents the
LLM from reasoning without critical rules that apply to every cycle.

The knowledge base is designed so that ALL documents are relevant to
every analysis. On a normal circumstance the entire knowledge base
would be fed to the LLM. Since token limits prevent that, this module
ensures the RAG retrieval never omits knowledge that the LLM needs.

Design principles:
- Master rulebook rejection rules apply to EVERY trade evaluation
- Confluence scoring rules apply to EVERY trade evaluation
- Risk management rules apply to EVERY trade evaluation
- DXY is MANDATORY for every USD pair (MR-PHIL-008)
- Wyckoff phase context is needed on every cycle
- Framework docs are needed for ALL detected frameworks, not just primary
- Trading style rules are needed for the active style on every cycle
- COT and macro guides are needed whenever macro data is present
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.rag.constants import DocumentType
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# USD pairs where DXY analysis is mandatory per MR-PHIL-008 and Section 2.2
_USD_PAIRS: frozenset[str] = frozenset({
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
    "USDJPY", "USDCAD", "USDCHF",
    "XAUUSD", "XAGUSD",
    # Normalised variants
    "EUR/USD", "GBP/USD", "AUD/USD", "NZD/USD",
    "USD/JPY", "USD/CAD", "USD/CHF",
    "XAU/USD", "XAG/USD",
})

# Metals where DXY inverse correlation is HIGH weight
_METAL_PAIRS: frozenset[str] = frozenset({
    "XAUUSD", "XAGUSD", "XAU/USD", "XAG/USD",
})


@dataclass(frozen=True, slots=True)
class MandatoryRequirements:
    """Specifies what MUST be retrieved for a given analysis cycle.

    Each entry in doc_type_min_chunks maps a DocumentType to the
    minimum number of chunks that must appear in the final result.
    If semantic retrieval does not return enough, the system must
    run supplemental targeted retrievals to fill the gaps.
    """

    doc_type_min_chunks: dict[str, int] = field(default_factory=dict)
    force_doc_types: frozenset[str] = field(default_factory=frozenset)
    force_rule_id_patterns: tuple[str, ...] = field(default_factory=tuple)
    is_usd_pair: bool = False
    is_metal_pair: bool = False
    detected_frameworks: frozenset[str] = field(default_factory=frozenset)


def compute_mandatory_requirements(
    *,
    symbol: str | None = None,
    has_smc_candidates: bool = False,
    has_snd_candidates: bool = False,
    has_macro_data: bool = False,
    has_cot_data: bool = False,
    has_rate_decision: bool = False,
    has_high_impact_event: bool = False,
    has_dxy_data: bool = False,
    style: str | None = None,
) -> MandatoryRequirements:
    """Compute mandatory retrieval requirements from TA+Macro signals.

    This function examines what the TA and Macro systems detected and
    determines which knowledge documents MUST have chunks in the final
    retrieval result. The RAG orchestrator uses this to run supplemental
    retrievals when semantic search alone does not cover everything.
    """
    min_chunks: dict[str, int] = {}
    force_types: set[str] = set()
    rule_patterns: list[str] = []
    detected_fw: set[str] = set()

    symbol_upper = (symbol or "").upper().replace("/", "")
    is_usd = symbol_upper in {s.replace("/", "") for s in _USD_PAIRS}
    is_metal = symbol_upper in {s.replace("/", "") for s in _METAL_PAIRS}

    # ── ALWAYS REQUIRED (every single cycle) ──────────────────────────

    # Master rulebook: rejection rules, confluence scoring, risk rules,
    # output format, session rules. These govern EVERY decision.
    min_chunks[DocumentType.MASTER_RULEBOOK] = 5
    force_types.add(DocumentType.MASTER_RULEBOOK)
    rule_patterns.extend([
        "MR-REJECT",     # All 10 rejection rules
        "MR-RISK",       # Risk management rules
        "MR-PHIL",       # Core philosophy
        "MR-AI",         # AI guardrails
    ])

    # Trading style rules: TP structure, R:R, session, management.
    # Needed every cycle because every trade must be evaluated against
    # the active style's constraints.
    min_chunks[DocumentType.TRADING_STYLE_RULES] = 3
    force_types.add(DocumentType.TRADING_STYLE_RULES)
    rule_patterns.extend([
        "STYLE-RR",      # R:R requirements
        "STYLE-RISK",    # Risk per trade by grade
        "STYLE-SESSION", # Session rules
        "STYLE-AVOID",   # Avoidance conditions
    ])

    # Wyckoff: contextual confirmation needed on every cycle.
    # Even when no explicit Wyckoff phase is detected, the LLM must
    # know the phase identification rules to determine if a phase
    # applies or not (WYCKOFF-PHASE-005: ambiguous = no bonus).
    min_chunks[DocumentType.WYCKOFF_GUIDE] = 2
    force_types.add(DocumentType.WYCKOFF_GUIDE)
    detected_fw.add("wyckoff")

    # ── FRAMEWORK-SPECIFIC (based on detected candidates) ─────────────

    if has_smc_candidates:
        min_chunks[DocumentType.SMC_FRAMEWORK] = 4
        force_types.add(DocumentType.SMC_FRAMEWORK)
        detected_fw.add("smc")
        rule_patterns.extend([
            "SMC-ENTRY",  # Entry logic
            "SMC-OB",     # Order block rules
            "SMC-LIQ",    # Liquidity rules
            "SMC-INV",    # Invalidation rules
        ])

    if has_snd_candidates:
        min_chunks[DocumentType.SND_RULEBOOK] = 4
        force_types.add(DocumentType.SND_RULEBOOK)
        detected_fw.add("snd")
        rule_patterns.extend([
            "SND-ENTRY",  # Entry logic
            "SND-ZONE",   # Zone definitions
            "SND-INV",    # Invalidation rules
            "SND-FILTER", # Quality filters
        ])

    # When BOTH frameworks have candidates, we need MORE chunks from each
    # because the LLM must cross-reference both frameworks.
    if has_smc_candidates and has_snd_candidates:
        min_chunks[DocumentType.SMC_FRAMEWORK] = 5
        min_chunks[DocumentType.SND_RULEBOOK] = 5

    # ── USD PAIR: DXY IS MANDATORY (MR-PHIL-008) ──────────────────────

    if is_usd or has_dxy_data:
        min_chunks[DocumentType.DXY_FRAMEWORK] = 3
        force_types.add(DocumentType.DXY_FRAMEWORK)
        detected_fw.add("dxy")
        rule_patterns.extend([
            "DXY-TREND",  # Trend interpretation
            "DXY-PAIR",   # Pair-specific correlation rules
            "DXY-STRUCT", # Structural confirmation
        ])

    # Metals get extra DXY weight (strong inverse correlation)
    if is_metal:
        min_chunks[DocumentType.DXY_FRAMEWORK] = 4
        rule_patterns.append("DXY-PAIR-009")  # Gold-specific rule

    # ── MACRO KNOWLEDGE ───────────────────────────────────────────────

    if has_macro_data:
        min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = 3
        force_types.add(DocumentType.MACRO_TO_PRICE_GUIDE)
        detected_fw.add("macro")
        rule_patterns.extend([
            "MACRO-BIAS",   # Bias generation rules
            "MACRO-LIMIT",  # Macro limitations
        ])

    # Rate decisions are the highest-impact macro events
    if has_rate_decision:
        min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = max(
            min_chunks.get(DocumentType.MACRO_TO_PRICE_GUIDE, 0), 4,
        )
        rule_patterns.extend([
            "MACRO-CB",     # Central bank policy rules
            "MACRO-RATE",   # Interest rate impact rules
            "MACRO-EVENT",  # High-impact event rules
        ])

    if has_high_impact_event:
        rule_patterns.append("MACRO-EVENT")
        # Ensure macro guide is present even if has_macro_data was False
        if DocumentType.MACRO_TO_PRICE_GUIDE not in min_chunks:
            min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = 2
            force_types.add(DocumentType.MACRO_TO_PRICE_GUIDE)

    if has_cot_data:
        min_chunks[DocumentType.COT_INTERPRETATION_GUIDE] = 3
        force_types.add(DocumentType.COT_INTERPRETATION_GUIDE)
        detected_fw.add("cot")
        rule_patterns.extend([
            "COT-EXTREME",  # Positioning extremes
            "COT-SHIFT",    # Positioning shifts
            "COT-TECH",     # Interaction with technical frameworks
            "COT-TREND",    # Trend confirmation
        ])

    # ── SCENARIO EXAMPLES ─────────────────────────────────────────────

    # Scenarios are always valuable for reasoning support.
    min_chunks[DocumentType.CHART_SCENARIO_LIBRARY] = 3
    force_types.add(DocumentType.CHART_SCENARIO_LIBRARY)

    requirements = MandatoryRequirements(
        doc_type_min_chunks=min_chunks,
        force_doc_types=frozenset(force_types),
        force_rule_id_patterns=tuple(sorted(set(rule_patterns))),
        is_usd_pair=is_usd,
        is_metal_pair=is_metal,
        detected_frameworks=frozenset(detected_fw),
    )

    logger.info(
        "mandatory_requirements_computed",
        symbol=symbol,
        is_usd_pair=is_usd,
        is_metal_pair=is_metal,
        force_doc_types=sorted(force_types),
        detected_frameworks=sorted(detected_fw),
        total_min_chunks=sum(min_chunks.values()),
        rule_patterns_count=len(requirements.force_rule_id_patterns),
    )

    return requirements
