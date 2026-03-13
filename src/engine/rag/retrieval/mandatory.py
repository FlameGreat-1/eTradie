"""Mandatory retrieval rules engine.

Determines which knowledge chunks MUST be present in every retrieval
result regardless of semantic similarity scores. This prevents the
LLM from reasoning without critical rules that apply to every cycle.

The knowledge base is designed so that ALL documents are relevant to
every analysis. On a normal circumstance the entire knowledge base
would be fed to the LLM. Since token limits prevent that, this module
ensures the RAG retrieval never omits knowledge that the LLM needs.

The LLM processes TA + Macro + RAG knowledge ALL TOGETHER in a single
pass. It does not analyze TA separately from macro. Therefore every
knowledge document is equally important and must be represented.

The system is pair-agnostic: it accepts ANY instrument the user selects
from the dashboard. USD detection is dynamic (checks if symbol contains
"USD"), not based on a hardcoded list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.rag.constants import DocumentType
from engine.shared.logging import get_logger

logger = get_logger(__name__)


def _symbol_contains_usd(symbol: str) -> bool:
    """Detect if a symbol involves USD.

    The system is pair-agnostic and accepts any instrument. This function
    dynamically checks whether USD appears in the symbol rather than
    matching against a hardcoded list. Works for any current or future
    USD pair regardless of broker naming convention.

    Examples:
        EURUSD -> True    EUR/USD -> True
        USDJPY -> True    USD/JPY -> True
        XAUUSD -> True    XAU/USD -> True
        GBPJPY -> False   NAS100  -> False
        DE40   -> False   BTCUSD  -> True
    """
    normalised = symbol.upper().replace("/", "").replace(".", "").replace("_", "")
    return "USD" in normalised


def _symbol_is_metal(symbol: str) -> bool:
    """Detect if a symbol is a precious metal.

    Metals have a strong inverse DXY correlation and need extra DXY
    knowledge. Checks for XAU (gold) and XAG (silver) dynamically.
    """
    normalised = symbol.upper().replace("/", "").replace(".", "").replace("_", "")
    return "XAU" in normalised or "XAG" in normalised


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

    The LLM processes TA + Macro + RAG knowledge ALL TOGETHER. It does
    not prioritize TA over macro or vice versa. Therefore this function
    ensures ALL knowledge categories are represented, not just the ones
    that match the current signals most closely.

    The system is pair-agnostic. USD detection is dynamic.
    """
    min_chunks: dict[str, int] = {}
    force_types: set[str] = set()
    rule_patterns: list[str] = []
    detected_fw: set[str] = set()

    # Dynamic pair detection - works for ANY instrument
    is_usd = _symbol_contains_usd(symbol) if symbol else False
    is_metal = _symbol_is_metal(symbol) if symbol else False

    # =====================================================================
    # ALWAYS REQUIRED (every single cycle, regardless of signals)
    # The knowledge base IS the LLM's brain. Without these, the LLM
    # cannot make correct decisions on ANY analysis.
    # =====================================================================

    # Master rulebook: rejection rules, confluence scoring, risk rules,
    # output format, session rules. These govern EVERY decision.
    min_chunks[DocumentType.MASTER_RULEBOOK] = 5
    force_types.add(DocumentType.MASTER_RULEBOOK)
    rule_patterns.extend([
        "MR-REJECT",
        "MR-RISK",
        "MR-PHIL",
        "MR-AI",
    ])

    # Trading style rules: TP structure, R:R, session, management.
    min_chunks[DocumentType.TRADING_STYLE_RULES] = 3
    force_types.add(DocumentType.TRADING_STYLE_RULES)
    rule_patterns.extend([
        "STYLE-RR",
        "STYLE-RISK",
        "STYLE-SESSION",
        "STYLE-AVOID",
    ])

    # Wyckoff: contextual confirmation needed on every cycle.
    # Even when no Wyckoff phase is detected, the LLM must know the
    # phase identification rules to determine if a phase applies.
    min_chunks[DocumentType.WYCKOFF_GUIDE] = 2
    force_types.add(DocumentType.WYCKOFF_GUIDE)
    detected_fw.add("wyckoff")

    # Macro-to-price guide: the LLM always needs to understand how
    # macro signals translate to price action, even when macro data
    # is neutral. Neutral macro is itself a signal (MACRO-BIAS-003).
    min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = 3
    force_types.add(DocumentType.MACRO_TO_PRICE_GUIDE)
    detected_fw.add("macro")
    rule_patterns.extend([
        "MACRO-BIAS",
        "MACRO-LIMIT",
    ])

    # Scenarios are always valuable for reasoning support.
    min_chunks[DocumentType.CHART_SCENARIO_LIBRARY] = 3
    force_types.add(DocumentType.CHART_SCENARIO_LIBRARY)

    # =====================================================================
    # FRAMEWORK-SPECIFIC (based on detected candidates)
    # =====================================================================

    if has_smc_candidates:
        min_chunks[DocumentType.SMC_FRAMEWORK] = 4
        force_types.add(DocumentType.SMC_FRAMEWORK)
        detected_fw.add("smc")
        rule_patterns.extend([
            "SMC-ENTRY",
            "SMC-OB",
            "SMC-LIQ",
            "SMC-INV",
        ])

    if has_snd_candidates:
        min_chunks[DocumentType.SND_RULEBOOK] = 4
        force_types.add(DocumentType.SND_RULEBOOK)
        detected_fw.add("snd")
        rule_patterns.extend([
            "SND-ENTRY",
            "SND-ZONE",
            "SND-INV",
            "SND-FILTER",
        ])

    # When BOTH frameworks have candidates, the LLM must cross-reference
    if has_smc_candidates and has_snd_candidates:
        min_chunks[DocumentType.SMC_FRAMEWORK] = 5
        min_chunks[DocumentType.SND_RULEBOOK] = 5

    # =====================================================================
    # USD PAIR: DXY IS MANDATORY (MR-PHIL-008)
    # Dynamic detection - works for ANY instrument containing USD
    # =====================================================================

    if is_usd or has_dxy_data:
        min_chunks[DocumentType.DXY_FRAMEWORK] = 3
        force_types.add(DocumentType.DXY_FRAMEWORK)
        detected_fw.add("dxy")
        rule_patterns.extend([
            "DXY-TREND",
            "DXY-PAIR",
            "DXY-STRUCT",
        ])

    # Metals get extra DXY weight (strong inverse correlation)
    if is_metal:
        min_chunks[DocumentType.DXY_FRAMEWORK] = 4
        rule_patterns.append("DXY-PAIR-009")

    # =====================================================================
    # ELEVATED MACRO REQUIREMENTS (when specific macro signals present)
    # =====================================================================

    if has_rate_decision:
        min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = max(
            min_chunks.get(DocumentType.MACRO_TO_PRICE_GUIDE, 0), 4,
        )
        rule_patterns.extend([
            "MACRO-CB",
            "MACRO-RATE",
            "MACRO-EVENT",
        ])

    if has_high_impact_event:
        rule_patterns.append("MACRO-EVENT")
        min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = max(
            min_chunks.get(DocumentType.MACRO_TO_PRICE_GUIDE, 0), 3,
        )

    if has_cot_data:
        min_chunks[DocumentType.COT_INTERPRETATION_GUIDE] = 3
        force_types.add(DocumentType.COT_INTERPRETATION_GUIDE)
        detected_fw.add("cot")
        rule_patterns.extend([
            "COT-EXTREME",
            "COT-SHIFT",
            "COT-TECH",
            "COT-TREND",
        ])

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
