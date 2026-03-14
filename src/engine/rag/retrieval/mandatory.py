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

CRITICAL DESIGN RULE: ALL 9 knowledge documents are ALWAYS included
in the mandatory requirements with baseline minimums. No document is
ever excluded. Signal flags only INCREASE minimums above the baseline.

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

    ALL 9 knowledge documents always have an entry. Signal flags
    only increase the minimums, never remove documents.
    """

    doc_type_min_chunks: dict[str, int] = field(default_factory=dict)
    force_doc_types: frozenset[str] = field(default_factory=frozenset)
    force_rule_id_patterns: tuple[str, ...] = field(default_factory=tuple)
    is_usd_pair: bool = False
    is_metal_pair: bool = False
    detected_frameworks: frozenset[str] = field(default_factory=frozenset)


def _raise_min(store: dict[str, int], key: str, value: int) -> None:
    """Set minimum to the higher of current and new value."""
    store[key] = max(store.get(key, 0), value)


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

    ALL 9 knowledge documents are ALWAYS included with baseline minimums.
    The knowledge base is the LLM's brain - withholding any document
    means the LLM reasons with an incomplete brain.

    Signal flags only INCREASE minimums above the baseline. They never
    cause a document to be excluded.

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
    # BASELINE: ALL 9 DOCUMENTS ALWAYS INCLUDED
    # The knowledge base IS the LLM's brain. Every document is relevant
    # to every analysis. The LLM needs the full picture to reason
    # correctly - even the absence of a signal is meaningful only if
    # the LLM knows the rules for that signal type.
    # =====================================================================

    # 1. Master rulebook: rejection rules, confluence scoring, risk rules,
    #    output format, session rules. Governs EVERY decision.
    min_chunks[DocumentType.MASTER_RULEBOOK] = 5
    force_types.add(DocumentType.MASTER_RULEBOOK)
    rule_patterns.extend(["MR-REJECT", "MR-RISK", "MR-PHIL", "MR-AI"])

    # 2. Trading style rules: TP structure, R:R, session, management.
    min_chunks[DocumentType.TRADING_STYLE_RULES] = 3
    force_types.add(DocumentType.TRADING_STYLE_RULES)
    rule_patterns.extend(["STYLE-RR", "STYLE-RISK", "STYLE-SESSION", "STYLE-AVOID"])

    # 3. SMC framework: even without SMC candidates, the LLM needs to
    #    understand SMC structure to interpret the technical snapshot
    #    (BOS events, swing points, liquidity sweeps are always present).
    min_chunks[DocumentType.SMC_FRAMEWORK] = 2
    force_types.add(DocumentType.SMC_FRAMEWORK)
    detected_fw.add("smc")

    # 4. SnD framework: even without SnD candidates, the LLM needs zone
    #    identification rules to understand why zones were or were not found.
    min_chunks[DocumentType.SND_RULEBOOK] = 2
    force_types.add(DocumentType.SND_RULEBOOK)
    detected_fw.add("snd")

    # 5. Wyckoff guide: contextual confirmation needed on every cycle.
    min_chunks[DocumentType.WYCKOFF_GUIDE] = 2
    force_types.add(DocumentType.WYCKOFF_GUIDE)
    detected_fw.add("wyckoff")

    # 6. DXY framework: needed for ALL pairs, not just USD pairs.
    #    For USD pairs: mandatory directional anchor (MR-PHIL-008).
    #    For non-USD crosses: global risk sentiment context (DXY-PAIR-008).
    #    For metals: strong inverse correlation (DXY-PAIR-009).
    #    The LLM must always know DXY rules to correctly weight DXY data.
    min_chunks[DocumentType.DXY_FRAMEWORK] = 2
    force_types.add(DocumentType.DXY_FRAMEWORK)
    detected_fw.add("dxy")

    # 7. COT interpretation guide: even without COT data, the LLM needs
    #    to know COT rules to understand what the absence of COT means
    #    and to correctly score confluence (COT is a PREFERRED factor).
    min_chunks[DocumentType.COT_INTERPRETATION_GUIDE] = 2
    force_types.add(DocumentType.COT_INTERPRETATION_GUIDE)
    detected_fw.add("cot")

    # 8. Macro-to-price guide: the LLM always needs macro translation
    #    rules. Even neutral macro is a signal (MACRO-BIAS-003).
    min_chunks[DocumentType.MACRO_TO_PRICE_GUIDE] = 3
    force_types.add(DocumentType.MACRO_TO_PRICE_GUIDE)
    detected_fw.add("macro")
    rule_patterns.extend(["MACRO-BIAS", "MACRO-LIMIT"])

    # 9. Chart scenarios: reasoning examples always valuable.
    min_chunks[DocumentType.CHART_SCENARIO_LIBRARY] = 3
    force_types.add(DocumentType.CHART_SCENARIO_LIBRARY)

    # =====================================================================
    # ELEVATED MINIMUMS: signal flags raise minimums above baseline
    # These NEVER remove documents - only increase chunk counts.
    # =====================================================================

    # SMC candidates detected -> need more SMC knowledge
    if has_smc_candidates:
        _raise_min(min_chunks, DocumentType.SMC_FRAMEWORK, 4)
        rule_patterns.extend(["SMC-ENTRY", "SMC-OB", "SMC-LIQ", "SMC-INV"])

    # SnD candidates detected -> need more SnD knowledge
    if has_snd_candidates:
        _raise_min(min_chunks, DocumentType.SND_RULEBOOK, 4)
        rule_patterns.extend(["SND-ENTRY", "SND-ZONE", "SND-INV", "SND-FILTER"])

    # Both frameworks -> LLM must cross-reference, need even more
    if has_smc_candidates and has_snd_candidates:
        _raise_min(min_chunks, DocumentType.SMC_FRAMEWORK, 5)
        _raise_min(min_chunks, DocumentType.SND_RULEBOOK, 5)

    # USD pair -> DXY is mandatory directional anchor
    if is_usd:
        _raise_min(min_chunks, DocumentType.DXY_FRAMEWORK, 3)
        rule_patterns.extend(["DXY-TREND", "DXY-PAIR", "DXY-STRUCT"])

    # Metal -> extra DXY weight (strong inverse correlation)
    if is_metal:
        _raise_min(min_chunks, DocumentType.DXY_FRAMEWORK, 4)
        rule_patterns.append("DXY-PAIR-009")

    # DXY data present (always collected) -> ensure DXY rules available
    if has_dxy_data:
        _raise_min(min_chunks, DocumentType.DXY_FRAMEWORK, 3)

    # Rate decisions -> highest-impact macro events
    if has_rate_decision:
        _raise_min(min_chunks, DocumentType.MACRO_TO_PRICE_GUIDE, 4)
        rule_patterns.extend(["MACRO-CB", "MACRO-RATE", "MACRO-EVENT"])

    # High-impact events -> need event rules
    if has_high_impact_event:
        _raise_min(min_chunks, DocumentType.MACRO_TO_PRICE_GUIDE, 3)
        rule_patterns.append("MACRO-EVENT")

    # COT data present -> need full COT interpretation
    if has_cot_data:
        _raise_min(min_chunks, DocumentType.COT_INTERPRETATION_GUIDE, 3)
        rule_patterns.extend(["COT-EXTREME", "COT-SHIFT", "COT-TECH", "COT-TREND"])

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
