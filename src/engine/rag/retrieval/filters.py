from __future__ import annotations

from engine.rag.constants import DocumentType, Framework, SetupFamily
from engine.rag.models.retrieval import RetrievalFilter


def build_rule_filters(
    *,
    framework: str | None = None,
    style: str | None = None,
    timeframe: str | None = None,
    direction: str | None = None,
) -> RetrievalFilter:
    doc_types = frozenset({
        DocumentType.MASTER_RULEBOOK,
        DocumentType.TRADING_STYLE_RULES,
    })
    frameworks = frozenset({framework}) if framework else frozenset()
    styles = frozenset({style}) if style else frozenset()
    timeframes = frozenset({timeframe}) if timeframe else frozenset()
    directions = frozenset({direction}) if direction else frozenset()

    return RetrievalFilter(
        doc_types=doc_types,
        frameworks=frameworks,
        styles=styles,
        timeframes=timeframes,
        directions=directions,
    )


def build_framework_filters(
    *,
    framework: str,
    setup_family: str | None = None,
    direction: str | None = None,
    timeframe: str | None = None,
) -> RetrievalFilter:
    doc_type_map: dict[str, DocumentType] = {
        Framework.SMC: DocumentType.SMC_FRAMEWORK,
        Framework.SND: DocumentType.SND_RULEBOOK,
        Framework.WYCKOFF: DocumentType.WYCKOFF_GUIDE,
        Framework.DXY: DocumentType.DXY_FRAMEWORK,
        Framework.COT: DocumentType.COT_INTERPRETATION_GUIDE,
        Framework.MACRO: DocumentType.MACRO_TO_PRICE_GUIDE,
        Framework.STYLE: DocumentType.TRADING_STYLE_RULES,
    }
    doc_type = doc_type_map.get(framework)
    doc_types = frozenset({doc_type}) if doc_type else frozenset()

    setup_families = frozenset({setup_family}) if setup_family else frozenset()
    directions = frozenset({direction}) if direction else frozenset()
    timeframes = frozenset({timeframe}) if timeframe else frozenset()

    return RetrievalFilter(
        doc_types=doc_types,
        frameworks=frozenset({framework}),
        setup_families=setup_families,
        directions=directions,
        timeframes=timeframes,
    )


def build_scenario_filters(
    *,
    framework: str | None = None,
    setup_family: str | None = None,
    direction: str | None = None,
    timeframe: str | None = None,
) -> RetrievalFilter:
    doc_types = frozenset({DocumentType.CHART_SCENARIO_LIBRARY})
    frameworks = frozenset({framework}) if framework else frozenset()

    setup_families = frozenset({setup_family}) if setup_family else frozenset()
    directions = frozenset({direction}) if direction else frozenset()
    timeframes = frozenset({timeframe}) if timeframe else frozenset()

    return RetrievalFilter(
        doc_types=doc_types,
        frameworks=frameworks,
        setup_families=setup_families,
        directions=directions,
        timeframes=timeframes,
    )


def build_macro_filters(
    *,
    style: str | None = None,
    direction: str | None = None,
) -> RetrievalFilter:
    doc_types = frozenset({
        DocumentType.MACRO_TO_PRICE_GUIDE,
        DocumentType.DXY_FRAMEWORK,
        DocumentType.COT_INTERPRETATION_GUIDE,
    })
    styles = frozenset({style}) if style else frozenset()
    directions = frozenset({direction}) if direction else frozenset()

    return RetrievalFilter(
        doc_types=doc_types,
        styles=styles,
        directions=directions,
    )
