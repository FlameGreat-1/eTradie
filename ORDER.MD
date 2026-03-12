```text
src/engine/rag/
├── __init__.py                         # Package marker for the RAG module within the engine service.
├── config.py                           # RAG-specific configuration: collection names, chunk sizes, overlap, retrieval top-k, rerank settings, embedding provider, vector store settings.
├── constants.py                        # RAG constants: document types, source names, metadata keys, retrieval modes, scenario outcome labels, framework identifiers.
├── orchestrator.py                     # Main RAG orchestration entrypoint: coordinates ingest, indexing, retrieval, re-embedding, and context assembly for processor use.
│
├── models/
│   ├── __init__.py                     # Package marker for RAG domain models.
│   ├── document.py                     # Canonical source-document model: id, type, title, source path, version, status, checksum, framework tags.
│   ├── document_version.py             # Version model for rulebooks/guides/scenario libraries; tracks changes, published status, superseded versions.
│   ├── chunk.py                        # Chunk model: normalized chunk content, hierarchy, metadata, token counts, embedding status.
│   ├── embedding.py                    # Embedding payload/result model: provider, vector dimension, hash, created_at, chunk linkage.
│   ├── retrieval.py                    # Retrieval result model: matched chunks, scores, rank, source metadata, framework/style/timeframe filters used.
│   ├── citation.py                     # Citation model used by processor outputs: cited chunk ids, document versions, section references, scenario references.
│   ├── scenario.py                     # Chart scenario domain model: scenario id, framework, setup family, direction, timeframe, outcome, linked image/text assets.
│   ├── context_bundle.py               # Final assembled context bundle model returned to processor: retrieved chunks, citations, gaps/conflicts, scenario matches.
│   └── coverage.py                     # Coverage/check model: indicates whether retrieved docs sufficiently cover the requested setup/context; drives NO SETUP fallback.
│
├── ingest/
│   ├── __init__.py                     # Package marker for RAG ingestion pipeline.
│   ├── pipeline.py                     # End-to-end ingest pipeline: load → normalize → chunk → embed → upsert → persist metadata/audit logs.
│   ├── manifest.py                     # Defines ingest manifest/bootstrap mapping of knowledge assets to doc types and source locations.
│   │
│   ├── loaders/
│   │   ├── __init__.py                 # Package marker for source loaders.
│   │   ├── base.py                     # Abstract loader interface for all supported source formats.
│   │   ├── markdown.py                 # Loads markdown rulebooks/guides and preserves section hierarchy.
│   │   ├── text.py                     # Loads plain-text rulebooks/source documents where markdown is unavailable.
│   │   ├── docx.py                     # Loads and extracts structured text from DOCX source documents when needed.
│   │   ├── json.py                     # Loads structured scenario/manifests/metadata JSON assets if used for scenario tagging or import.
│   │   └── scenario_asset.py           # Loads chart scenario bundles: explanation text, image refs, tags, expected outcome metadata.
│   │
│   ├── normalizers/
│   │   ├── __init__.py                 # Package marker for ingestion normalizers.
│   │   ├── base.py                     # Common normalizer contract.
│   │   ├── rules.py                    # Normalizes rulebooks/guides: section labels, numbering, bullet cleanup, heading hierarchy, canonical terminology.
│   │   ├── scenarios.py                # Normalizes scenario metadata: framework tags, setup family, direction, timeframes, valid/failed/edge-case labels.
│   │   ├── macro.py                    # Normalizes macro-focused knowledge docs: currency mapping, DXY/COT terminology, event naming conventions.
│   │   └── taxonomy.py                 # Canonical taxonomy mapper for shared labels across all knowledge assets.
│   │
│   ├── chunkers/
│   │   ├── __init__.py                 # Package marker for chunking strategies.
│   │   ├── base.py                     # Common chunker interface and shared chunking utilities.
│   │   ├── rulebook.py                 # Chunks master rulebook by section/subsection/rule group while preserving hierarchy.
│   │   ├── framework.py                # Chunks SMC/SnD/Wyckoff/DXY/COT docs by concept, setup family, and rule scope.
│   │   ├── macro.py                    # Chunks macro-to-price and style guides by concept blocks and decision rules.
│   │   ├── scenario.py                 # Chunks chart scenario library one scenario per primary retrievable unit plus supplemental notes.
│   │   └── metadata.py                 # Attaches mandatory metadata to chunks after chunk generation.
│   │
│   └── validators/
│       ├── __init__.py                 # Package marker for ingest validation.
│       ├── document.py                 # Validates source documents before ingest: required headers, type mapping, version presence, checksum.
│       ├── chunk.py                    # Validates generated chunks: empty text, oversize/undersize checks, missing metadata, hierarchy consistency.
│       └── scenario.py                 # Validates scenario completeness: required tags, explanation text, linked image refs, outcome labels.
│
├── embeddings/
│   ├── __init__.py                     # Package marker for embedding logic.
│   ├── base.py                         # Abstract embedding provider interface.
│   ├── pipeline.py                     # Embedding workflow: batching, retry, hashing, idempotency, vector generation, status persistence.
│   ├── factory.py                      # Resolves active embedding provider from config.
│   ├── openai.py                       # OpenAI embedding adapter implementation if enabled.
│   ├── nomic.py                        # Nomic/local embedding adapter implementation if enabled.
│   ├── sentence_transformers.py        # Optional local sentence-transformers adapter for self-hosted embeddings.
│   └── validator.py                    # Validates embedding outputs: vector size, NaN checks, provider metadata, duplicate prevention.
│
├── vectorstore/
│   ├── __init__.py                     # Package marker for vector store integration.
│   ├── base.py                         # Abstract vector store contract: create collection, upsert, delete, query, health check.
│   ├── factory.py                      # Resolves active vector store implementation from config.
│   ├── chroma.py                       # ChromaDB adapter implementation for collection management and vector operations.
│   ├── collections.py                  # Collection bootstrap definitions: documents/scenarios collections, metadata schema expectations.
│   ├── upsert.py                       # Encapsulates vector upsert/update/delete workflows and idempotent syncing.
│   ├── filters.py                      # Builds vector-store-compatible metadata filters from retrieval constraints.
│   └── health.py                       # Vector store connectivity and readiness checks.
│
├── retrieval/
│   ├── __init__.py                     # Package marker for retrieval pipeline.
│   ├── retriever.py                    # Primary retrieval service: queries vector store, applies filters, returns ranked chunk candidates.
│   ├── query_builder.py                # Builds retrieval queries from processor inputs: framework, style, timeframe, direction, setup family, macro context.
│   ├── filters.py                      # Retrieval filter constructors: doc_type, framework, style, timeframe, direction, scenario outcome, version.
│   ├── reranker.py                     # Optional reranking stage for retrieved chunks using secondary scoring model or rule-based reranking.
│   ├── assembler.py                    # Assembles final retrieval results into coherent context blocks for processor consumption.
│   ├── citations.py                    # Builds normalized citations from retrieved chunks/doc versions for downstream audit and processor output.
│   ├── coverage.py                     # Checks whether retrieved material sufficiently covers the requested scenario/rules; flags missing coverage → NO SETUP.
│   ├── conflict.py                     # Detects conflicting retrieved rules/examples across frameworks, styles, or timeframes.
│   └── strategies/
│       ├── __init__.py                 # Package marker for retrieval strategies.
│       ├── rule_first.py               # Retrieval strategy prioritizing strict rulebook sections before examples/scenarios.
│       ├── scenario_first.py           # Retrieval strategy prioritizing scenario examples when candidate family is already known.
│       ├── macro_bias.py               # Retrieval strategy focused on macro/DXY/COT/style guidance for macro-heavy analysis cycles.
│       └── hybrid.py                   # Combined retrieval strategy blending rulebook, framework, and scenario retrieval.
│
├── scenarios/
│   ├── __init__.py                     # Package marker for chart scenario handling.
│   ├── config.py                       # Scenario-specific config: required metadata, supported tags, image policies, scenario collection settings.
│   ├── tags.py                         # Canonical scenario taxonomy: framework, setup family, direction, timeframe, style, outcome, confluence tags.
│   ├── matcher.py                      # Matches retrieved TA candidate context to relevant chart scenarios/examples.
│   ├── indexer.py                      # Builds and maintains scenario-specific indexes/metadata for fast lookup and retrieval.
│   ├── validator.py                    # Validates scenario assets and tag completeness before they are allowed into the KB.
│   └── assets/
│       ├── __init__.py                 # Package marker for scenario asset helpers.
│       ├── manifest.py                 # Scenario asset manifest utilities linking explanation docs to image references and metadata.
│       └── resolver.py                 # Resolves scenario asset paths/refs for ingestion and retrieval.
│
├── prompts/
│   ├── __init__.py                     # Package marker for RAG-related prompt assets/guardrails.
│   ├── system.py                       # System prompt fragments governing strict RAG usage: reason only from retrieved docs + live data.
│   ├── constraints.py                  # Hard constraints: NO SETUP on missing coverage/conflicts, cite rules/examples, no hallucinated frameworks.
│   ├── citations.py                    # Prompt instructions for requiring citation-ready output structures from processor.
│   └── templates.py                    # Reusable prompt templates for retrieval summaries, coverage checks, and context packaging.
│
├── services/
│   ├── __init__.py                     # Package marker for higher-level RAG services.
│   ├── bootstrap.py                    # Initializes collections, seeds manifests, performs first ingest/bootstrap checks.
│   ├── reembed.py                      # Handles re-embedding workflow after source document updates/version changes.
│   ├── versioning.py                   # Coordinates document version lifecycle, supersession rules, active-version selection.
│   ├── health.py                       # RAG health checks spanning loader, embedder, vector store, retrieval readiness.
│   ├── sync.py                         # Synchronizes source docs/metadata with vector and relational stores; reconciles stale/deleted chunks.
│   └── audit.py                        # Cross-cutting audit helpers for retrieval trails, ingest events, citation lineage, version provenance.
│
├── storage/
│   ├── __init__.py                     # Package marker for RAG relational persistence layer.
│   ├── repositories/
│   │   ├── __init__.py                 # Package marker for RAG repositories.
│   │   ├── document.py                 # Repository for source document registry and active/inactive document state.
│   │   ├── document_version.py         # Repository for document version history and supersession tracking.
│   │   ├── chunk.py                    # Repository for chunk metadata, hashes, embedding status, and source linkage.
│   │   ├── scenario.py                 # Repository for scenario metadata and asset linkage.
│   │   ├── ingest_job.py               # Repository for ingest/reindex job state, retries, failures, and timestamps.
│   │   ├── retrieval_log.py            # Repository for retrieval audit logs per analysis cycle/request.
│   │   ├── citation_log.py             # Repository for chunk/document citations used by processor outputs.
│   │   └── reembed_queue.py            # Repository for queued documents/chunks awaiting re-embedding after updates.
│   └── schemas/
│       ├── __init__.py                 # Package marker for RAG ORM/database schemas.
│       ├── document.py                 # DB schema for registered RAG source documents.
│       ├── document_version.py         # DB schema for document version records.
│       ├── chunk.py                    # DB schema for chunk metadata and embedding lifecycle tracking.
│       ├── scenario.py                 # DB schema for chart scenario metadata and linked assets.
│       ├── ingest_job.py               # DB schema for ingest/reindex job tracking.
│       ├── retrieval_log.py            # DB schema for retrieval audit logging.
│       ├── citation_log.py             # DB schema for citation lineage and analysis-cycle references.
│       └── reembed_queue.py            # DB schema for pending re-embedding tasks.
│
├── knowledge/
│   ├── __init__.py                     # Package marker for knowledge asset definitions/helpers.
│   ├── manifest.py                     # Central knowledge asset registry describing the required KB groups and their source locations.
│   ├── types.py                        # Enumerations/types for knowledge groups: master_rulebook, smc_framework, snd_rulebook, wyckoff_guide, etc.
│   ├── policies.py                     # Knowledge governance rules: mandatory assets, version requirements, publish/activation rules.
│   └── bootstrap/
│       ├── __init__.py                 # Package marker for initial KB bootstrap helpers.
│       ├── seed.py                     # Seeds default knowledge asset records for the initial required document groups.
│       └── validator.py                # Validates that mandatory knowledge groups are present before analysis can be marked ready.
│
└── tests_support/
    ├── __init__.py                     # Package marker for RAG test-only support helpers if you keep them close to the module.
    ├── fixtures.py                     # Shared ingest/retrieval/scenario fixtures for RAG tests.
    └── factories.py                    # Factory helpers for generating mock docs, chunks, scenarios, retrieval responses.
```

## What this structure is designed to support

This tree is built to support the full knowledge base your spec implies:

* **master_rulebook**
* **smc_framework**
* **snd_framework**
* **wyckoff_guide**
* **dxy_framework**
* **cot_interpretation_guide**
* **trading_style_rules**
* **macro_to_price_guide**
* **chart_scenario**

## Important architecture note

This `rag/` tree assumes the same engine-wide shared infrastructure already exists and is reused:

* `src/engine/shared/db`
* `src/engine/shared/cache`
* `src/engine/shared/http`
* `src/engine/shared/logging`
* `src/engine/shared/metrics`
* `src/engine/shared/scheduler`
* `src/engine/shared/tracing`

So `rag/` should **not** create duplicate infra layers for those concerns.

## Boundary summary

* `rag/ingest` = load, normalize, chunk, validate
* `rag/embeddings` = generate vectors
* `rag/vectorstore` = store/query vectors
* `rag/retrieval` = fetch and assemble context
* `rag/scenarios` = scenario-library handling
* `rag/storage` = relational audit/version metadata
* `rag/knowledge` = authoritative knowledge-asset registry/governance
* `rag/services` = bootstrap, sync, reembed, health, audit
