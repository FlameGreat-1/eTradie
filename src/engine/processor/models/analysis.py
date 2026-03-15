"""Canonical Module A Analysis Output schema.

This is the complete structured output the LLM must produce on every
analysis cycle. Every field is always present per Rulebook Section 12.3.
When direction is NO SETUP, trade-specific fields are null but keys exist.

The LLM raw JSON is parsed and validated into this model before being
mapped to the gateway's ProcessorOutput for routing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from engine.shared.models.base import FrozenModel, TimestampedModel


class EvidenceItem(FrozenModel):
    """A single piece of evidence citing a RAG document."""

    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    section: Optional[str] = None
    rule_id: Optional[str] = None
    content_preview: Optional[str] = None


class CurrencyBias(FrozenModel):
    """Macro bias assessment for a single currency."""

    bias: str  # BULLISH / BEARISH / NEUTRAL
    evidence: list[EvidenceItem] = Field(default_factory=list)


class MacroBiasOutput(FrozenModel):
    """Macro bias for both currencies in the pair."""

    base_currency: CurrencyBias
    quote_currency: CurrencyBias


class DXYBiasOutput(FrozenModel):
    """DXY directional assessment."""

    direction: str  # BULLISH / BEARISH / NEUTRAL
    evidence: list[EvidenceItem] = Field(default_factory=list)


class COTSignalOutput(FrozenModel):
    """COT positioning summary."""

    summary: str
    week_over_week: Optional[str] = None  # increase / decrease / flat
    extreme_flag: bool = False
    evidence: list[EvidenceItem] = Field(default_factory=list)


class EventRiskItem(FrozenModel):
    """A single upcoming high-impact event."""

    event: str
    time: Optional[str] = None
    impact: str = "HIGH"
    currency: Optional[str] = None


class TimeframeBias(FrozenModel):
    """Structural bias for a single timeframe."""

    structure: str  # bullish / bearish / neutral / choch_bullish / choch_bearish
    key_levels: list[float] = Field(default_factory=list)
    notes: str = ""


class SetupZone(FrozenModel):
    """Identified trade setup zone on the entry timeframe."""

    type: Optional[str] = None  # OB / FVG / SnD / liquidity_sweep
    zone_id: Optional[str] = None
    quality: Optional[str] = None  # A / B / Invalid
    bounds: list[float] = Field(default_factory=list)  # [lower, upper]
    evidence: list[EvidenceItem] = Field(default_factory=list)


class WyckoffPhaseOutput(FrozenModel):
    """Wyckoff phase identification."""

    phase: str  # accumulation / markup / distribution / markdown / spring / upthrust / ranging
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ConfluenceFactor(FrozenModel):
    """A single scored confluence factor."""

    name: str
    present: bool = False
    value: float = 0.0
    notes: str = ""


class ConfluenceScoreOutput(FrozenModel):
    """Confluence scoring result."""

    score: float = Field(ge=0.0, le=10.0)
    factors: list[ConfluenceFactor] = Field(default_factory=list)


class EntryZone(FrozenModel):
    """Precise entry price range."""

    low: Optional[float] = None
    high: Optional[float] = None


class StopLossOutput(FrozenModel):
    """Stop loss with structural reasoning."""

    price: Optional[float] = None
    reason: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)


class TakeProfitLevel(FrozenModel):
    """A single take profit target."""

    level: Optional[float] = None
    size_pct: int = 0  # percentage of position to close
    basis: str = ""  # structural reasoning


class RAGSourceCitation(FrozenModel):
    """A RAG document cited in the analysis."""

    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    section: Optional[str] = None
    relevance_score: Optional[float] = None


class RetrievalAudit(FrozenModel):
    """Audit data for the RAG retrieval that fed this analysis."""

    query_summary: str = ""
    strategy_used: Optional[str] = None
    top_k: int = 0
    chunks_returned: list[RAGSourceCitation] = Field(default_factory=list)


class AnalysisAudit(FrozenModel):
    """Full audit trail for the analysis."""

    retrieval: RetrievalAudit = Field(default_factory=RetrievalAudit)
    citations: list[RAGSourceCitation] = Field(default_factory=list)


class AnalysisOutput(TimestampedModel):
    """Complete Module A analysis output.

    This is the canonical schema per Rulebook Section 12.3 and LLM.md.
    Every field is always present. When direction is NO SETUP,
    trade-specific fields are null but keys exist.
    """

    # Identity
    analysis_id: str
    pair: str
    timestamp: datetime
    trading_style: str
    session: str

    # Macro assessment
    macro_bias: MacroBiasOutput
    dxy_bias: DXYBiasOutput
    cot_signal: COTSignalOutput
    event_risk: list[EventRiskItem] = Field(default_factory=list)

    # Technical structure
    htf_bias: TimeframeBias
    mtf_bias: TimeframeBias
    entry_setup: SetupZone
    wyckoff_phase: WyckoffPhaseOutput

    # Scoring
    confluence_score: ConfluenceScoreOutput
    setup_grade: str  # A+ / A / B / REJECT
    direction: str  # LONG / SHORT / NO SETUP

    # Trade construction
    entry_zone: EntryZone
    stop_loss: StopLossOutput
    take_profits: list[TakeProfitLevel] = Field(default_factory=list)
    rr_ratio: Optional[float] = None

    # Decision
    confidence: str  # HIGH / MEDIUM / LOW / NO SETUP
    proceed_to_module_b: str  # YES / NO
    explainable_reasoning: str = ""

    # Traceability
    rag_sources: list[RAGSourceCitation] = Field(default_factory=list)
    audit: AnalysisAudit = Field(default_factory=AnalysisAudit)
