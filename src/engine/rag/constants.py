from __future__ import annotations

from enum import StrEnum, unique


@unique
class DocumentType(StrEnum):
    MASTER_RULEBOOK = "master_rulebook"
    SMC_FRAMEWORK = "smc_framework"
    SND_RULEBOOK = "snd_rulebook"
    WYCKOFF_GUIDE = "wyckoff_guide"
    DXY_FRAMEWORK = "dxy_framework"
    COT_INTERPRETATION_GUIDE = "cot_interpretation_guide"
    TRADING_STYLE_RULES = "trading_style_rules"
    MACRO_TO_PRICE_GUIDE = "macro_to_price_guide"
    CHART_SCENARIO_LIBRARY = "chart_scenario_library"


@unique
class DocumentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@unique
class IngestJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@unique
class EmbeddingStatus(StrEnum):
    PENDING = "pending"
    EMBEDDED = "embedded"
    FAILED = "failed"
    STALE = "stale"


@unique
class RetrievalStrategy(StrEnum):
    RULE_FIRST = "rule_first"
    SCENARIO_FIRST = "scenario_first"
    MACRO_BIAS = "macro_bias"
    HYBRID = "hybrid"


@unique
class CoverageResult(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    PARTIAL = "partial"


@unique
class ConflictResult(StrEnum):
    NONE_DETECTED = "none_detected"
    CONFLICT_FOUND = "conflict_found"


@unique
class Framework(StrEnum):
    SMC = "smc"
    SND = "snd"
    WYCKOFF = "wyckoff"
    DXY = "dxy"
    COT = "cot"
    MACRO = "macro"
    STYLE = "style"


@unique
class SetupFamily(StrEnum):
    ORDER_BLOCK = "order_block"
    FAIR_VALUE_GAP = "fair_value_gap"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    BREAKER_BLOCK = "breaker_block"
    SUPPLY_ZONE = "supply_zone"
    DEMAND_ZONE = "demand_zone"
    SPRING = "spring"
    UPTHRUST = "upthrust"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    MARKUP = "markup"
    MARKDOWN = "markdown"


@unique
class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@unique
class ScenarioOutcome(StrEnum):
    VALID_WIN = "valid_win"
    VALID_LOSS = "valid_loss"
    FAILED_SETUP = "failed_setup"
    EDGE_CASE = "edge_case"


@unique
class SourceFormat(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    DOCX = "docx"
    JSON = "json"
    SCENARIO_BUNDLE = "scenario_bundle"


@unique
class CollectionName(StrEnum):
    DOCUMENTS = "etradie_documents"
    SCENARIOS = "etradie_scenarios"


METADATA_KEY_DOC_ID = "doc_id"
METADATA_KEY_DOC_TYPE = "doc_type"
METADATA_KEY_DOC_VERSION = "doc_version"
METADATA_KEY_CHUNK_INDEX = "chunk_index"
METADATA_KEY_CHUNK_HASH = "chunk_hash"
METADATA_KEY_SECTION = "section"
METADATA_KEY_SUBSECTION = "subsection"
METADATA_KEY_FRAMEWORK = "framework"
METADATA_KEY_RULE_IDS = "rule_ids"
METADATA_KEY_PATTERN_NAME = "pattern_name"
METADATA_KEY_PATTERN_FAMILY = "pattern_family"
METADATA_KEY_SETUP_FAMILY = "setup_family"
METADATA_KEY_DIRECTION = "direction"
METADATA_KEY_TIMEFRAMES = "timeframes"
METADATA_KEY_STYLE = "style"
METADATA_KEY_INSTRUMENT_SCOPE = "instrument_scope"
METADATA_KEY_SCENARIO_ID = "scenario_id"
METADATA_KEY_SCENARIO_OUTCOME = "scenario_outcome"
METADATA_KEY_SOURCE_PATH = "source_path"
METADATA_KEY_UPDATED_AT = "updated_at"

MANDATORY_KNOWLEDGE_GROUPS: frozenset[DocumentType] = frozenset({
    DocumentType.MASTER_RULEBOOK,
    DocumentType.SMC_FRAMEWORK,
    DocumentType.SND_RULEBOOK,
    DocumentType.WYCKOFF_GUIDE,
    DocumentType.DXY_FRAMEWORK,
    DocumentType.COT_INTERPRETATION_GUIDE,
    DocumentType.TRADING_STYLE_RULES,
    DocumentType.MACRO_TO_PRICE_GUIDE,
})

SUPPORTED_IMAGE_FORMATS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".svg",
})
