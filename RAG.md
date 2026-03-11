IMPORTANT ARCHITECTURE RULE:

THE RAG MODULE DOES NOT PERFORM AI ANALYSIS OR DECISION MAKING.

ITS RESPONSIBILITY IS STRICTLY TO RETRIEVE AND PROVIDE RELEVANT KNOWLEDGE CONTEXT FROM THE KNOWLEDGE BASE.

RAG ONLY RETURNS STRUCTURED CONTEXT (RULES, FRAMEWORK DEFINITIONS, AND SCENARIO EXAMPLES) THAT THE AI MODEL WILL USE DURING ANALYSIS.

ALL AI REASONING, INTERPRETATION, AND FINAL DECISION LOGIC ARE HANDLED EXCLUSIVELY BY THE PROCESSOR MODULE.

RAG IS A KNOWLEDGE RETRIEVAL SYSTEM, NOT AN AI ANALYSIS ENGINE.


Shared infrastructure:

Config, exceptions, logging, metrics, tracing, HTTP client (with circuit breaker + backoff), RSS parser, Redis cache, DB connection manager, base repository, APScheduler wrapper, Alembic migrations



# RAG Implementation Specification

## Purpose

The **Retrieval-Augmented Generation (RAG) module** provides the **knowledge base used by the trading AI analysis engine**.

It stores structured trading knowledge and retrieves only the **relevant rules, frameworks, and chart examples** during analysis.

The AI **must reason strictly from retrieved knowledge and live market data**.

If knowledge coverage is missing or rules conflict, the system must output:

```
NO SETUP
```

This prevents hallucination and ensures all trading decisions are **rulebook-backed**.

---

# 1. Knowledge Assets

The knowledge base must contain **exactly these document groups**.

These documents represent the **entire trading knowledge domain**.

### 1. Master Rulebook

Contains:

* overall system rules
* confluence scoring
* risk constraints
* entry restrictions
* session rules
* macro-technical interaction rules

This document acts as the **primary authority**.

---

### 2. SMC Framework Document

Defines the **Smart Money Concepts framework** including:

* BMS
* CHOCH
* SMS
* inducement
* liquidity sweeps
* order blocks
* fair value gaps
* breaker blocks
* mitigation
* AMD phases
* turtle soup setups

---

### 3. Supply & Demand Rulebook

Defines the **SnD methodology** including:

* Quasimodo structures
* QML / QMH
* SR flips
* RS flips
* MPL structures
* fakeout sequences
* previous highs/lows clusters
* marubozu confirmation
* compression zones
* supply and demand zones
* continuation setups

---

### 4. Wyckoff Phase Guide

Defines Wyckoff structure phases:

* accumulation
* distribution
* spring
* upthrust
* SOS
* SOW
* LPS
* LPSY

Also defines **when trading is allowed or prohibited** within each phase.

---

### 5. DXY Analysis Framework

Defines how **DXY structure influences USD pairs**.

Includes:

* DXY trend interpretation
* USD bias propagation to pairs
* metals correlation
* cross-asset relationships

---

### 6. COT Interpretation Guide

Defines how to interpret **Commitments of Traders data**:

* non-commercial positioning
* extreme positioning thresholds
* week-over-week changes
* reversal risk conditions

---

### 7. Chart Scenario Library

A curated dataset of **real chart examples**.

Each scenario contains:

* annotated chart
* explanation
* pattern classification
* confluence analysis
* outcome

Minimum required:

```
20 chart scenarios
```

Each scenario must represent:

* valid setups
* failed setups
* edge cases

---

### 8. Trading Style Rules

Defines trading styles and their rules:

* scalping
* intraday
* swing
* positional

Includes:

* permitted timeframes
* allowed setups
* target structures
* holding rules
* risk expectations

---

### 9. Macro-to-Price Relationship Guide

Defines how **macro signals interact with technical setups**.

Examples:

* macro bias alignment rules
* macro override conditions
* event risk rules
* macro-technical conflict resolution

---

# 2. Storage Architecture

The RAG system uses **two storage layers**.

---

# Vector Database (ChromaDB)

Stores:

* embedded document chunks
* vector embeddings
* metadata for retrieval filters

Purpose:

```
semantic similarity search
```

Used for retrieving:

* rulebook sections
* framework definitions
* chart scenario examples

---

# PostgreSQL

Stores **operational metadata**, not embeddings.

Tables include:

* rag_documents
* rag_document_versions
* rag_chunks
* rag_ingest_jobs
* rag_retrieval_logs
* rag_analysis_citations
* rag_reembed_queue

PostgreSQL enables:

* document versioning
* ingestion tracking
* audit logging
* citation lineage
* re-embedding workflows

---

# 3. Knowledge Preparation

All documents must be converted into **structured markdown format**.

Required files:

```
master_rulebook.md
smc_framework.md
snd_rulebook.md
wyckoff_guide.md
dxy_framework.md
cot_guide.md
trading_style_rules.md
macro_to_price_guide.md
```

---

# Chart Scenario Library Format

```
chart_scenarios/

  scenario_01/
    explanation.md
    chart.png
    metadata.json

  scenario_02/
    explanation.md
    chart.png
    metadata.json
```

Metadata must include:

* framework
* setup_family
* direction
* timeframe
* outcome
* confluence_tags

---

# 4. Chunking Rules

Chunking must preserve **semantic structure**.

Never chunk purely by token size.

---

## Rulebooks

Chunk by:

```
section
subsection
rule group
```

---

## Framework Documents

Chunk by:

```
concept
pattern
setup definition
```

---

## Macro Guides

Chunk by:

```
macro concept
macro rule
interpretation block
```

---

## Scenario Library

Each scenario must produce **one primary retrievable chunk**.

Supplementary explanation may produce additional chunks.

---

# 5. Chunk Metadata

Every chunk must include the following metadata.

```
doc_id
doc_type
doc_version
framework
section
subsection
rule_ids
pattern_name
pattern_family
direction
style
timeframes
instrument_scope
scenario_outcome
source_path
updated_at
```

This metadata enables **precise retrieval filtering**.

---

# 6. Embedding Pipeline

The embedding pipeline performs the following steps.

1. load document
2. normalize content
3. generate structured chunks
4. attach metadata
5. generate embeddings
6. store embeddings in ChromaDB
7. persist metadata in PostgreSQL

The pipeline must be **idempotent**.

Duplicate chunks must not be inserted.

---

# 7. Retrieval Requirements

Retrieval must support **metadata filters**.

Filters include:

```
framework
style
timeframe
direction
setup_family
scenario_outcome
```

Example query:

```
framework = smc
timeframe = 4H
direction = bullish
setup_family = turtle_soup
```

Retrieval returns the **top-k most relevant chunks**.

---

# 8. Scenario Library Retrieval

Scenario retrieval must support matching by:

* framework
* setup family
* timeframe
* direction
* confluence tags

Example:

```
setup_family = qm_fakeout
direction = bearish
timeframe = 1H
```

Returned scenarios provide **visual examples for reasoning support**.

---

# 9. Coverage Verification

After retrieval, the system must verify **knowledge coverage**.

Coverage checks include:

* rule coverage
* framework coverage
* timeframe compatibility

If coverage is insufficient:

```
output = NO SETUP
```

---

# 10. Conflict Detection

Conflicts occur when:

* HTF and LTF rules disagree
* macro bias contradicts setup direction
* rulebook definitions conflict
* retrieved rules produce incompatible signals

When conflict occurs:

```
output = NO SETUP
```

---

# 11. Citation Requirements

Every final decision must cite supporting knowledge.

Citations must include:

```
document
section
rule_id
```

Examples:

```
SMC_Framework.md
Section 3.2
Rule SMC-12
```

Citations must be persisted in PostgreSQL.

---

# 12. Document Versioning

Every document must support **version control**.

When a document is updated:

1. mark previous version inactive
2. create new version record
3. regenerate chunks
4. regenerate embeddings
5. update vector store
6. log version change

---

# 13. Guardrails

The following constraints are mandatory.

AI must not invent rules.

AI must only reason using:

```
retrieved knowledge
+
live market data
```

If knowledge coverage is missing:

```
NO SETUP
```

Every confluence factor must be verifiable using live data.

Conflicting signals invalidate setups.

Model temperature must remain:

```
0
```

---

# 14. Output Contract

The RAG system must output a **Context Bundle**.

The context bundle contains:

* retrieved rule chunks
* retrieved framework definitions
* retrieved scenario examples
* citation references
* coverage flags
* conflict flags

The **processor module consumes this bundle** to produce the final decision.

---

# 15. Implementation Summary

The RAG module must implement:

```
knowledge asset preparation
document ingestion pipeline
structure-aware chunking
embedding generation
vector storage (ChromaDB)
metadata persistence (PostgreSQL)
semantic retrieval
scenario retrieval
coverage validation
conflict detection
citation tracking
document versioning
re-embedding workflow
context bundle output
```
