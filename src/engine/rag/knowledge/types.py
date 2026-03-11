from __future__ import annotations

from engine.rag.constants import DocumentType

KNOWLEDGE_GROUP_DESCRIPTIONS: dict[str, str] = {
    DocumentType.MASTER_RULEBOOK: "Primary authority for all trading rules and constraints",
    DocumentType.SMC_FRAMEWORK: "Smart Money Concepts framework definitions",
    DocumentType.SND_RULEBOOK: "Supply and Demand methodology definitions",
    DocumentType.WYCKOFF_GUIDE: "Wyckoff phase structure and trading permissions",
    DocumentType.DXY_FRAMEWORK: "DXY structure influence on USD pairs",
    DocumentType.COT_INTERPRETATION_GUIDE: "Commitments of Traders data interpretation",
    DocumentType.TRADING_STYLE_RULES: "Trading style rules and permitted setups",
    DocumentType.MACRO_TO_PRICE_GUIDE: "Macro signal to technical setup interaction rules",
    DocumentType.CHART_SCENARIO_LIBRARY: "Curated chart scenario examples",
}
