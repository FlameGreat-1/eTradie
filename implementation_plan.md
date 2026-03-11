# Unit of Work Pattern — RAG Session Fix

## Problem

[main.py](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/main.py) creates sessions via `async with container.db.session()` which close when the block exits. All 8 RAG repos are bound to a dead session. Any DB operation at runtime fails.

## Solution: Unit of Work (UoW) Pattern

Each service method that needs DB access creates a **fresh session → fresh repos → auto-commit/rollback → close** via `async with self._uow() as uow:`.

## Proposed Changes

### RAG Storage Layer

#### [NEW] [uow.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/storage/uow.py)

`RAGUnitOfWork` — wraps all 8 repos with a single session lifecycle:
- `__aenter__`: creates `AsyncSession`, instantiates all repos
- `__aexit__`: commit on success, rollback on error, close session
- Exposes: `document_repo`, `version_repo`, `chunk_repo`, `scenario_repo`, `ingest_job_repo`, `retrieval_log_repo`, `citation_log_repo`, `reembed_queue_repo`
- Factory function `rag_uow_factory(db: DatabaseManager)` returns a callable that creates `RAGUnitOfWork` instances

---

### RAG Services (6 files)

Each service changes from [__init__(*, repo_a, repo_b)](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/embeddings/sentence_transformers.py#15-20) → [__init__(*, uow_factory)](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/embeddings/sentence_transformers.py#15-20). Each method wraps DB calls in `async with self._uow() as uow:`.

#### [MODIFY] [audit.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/audit.py)

- Constructor: `uow_factory` instead of `retrieval_log_repo` + `citation_log_repo`
- [log_retrieval()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/audit.py#25-53): wrap in UoW context
- [log_citations()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/audit.py#54-83): wrap in UoW context

#### [MODIFY] [bootstrap.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/bootstrap.py)

- Constructor: `uow_factory` instead of `document_repo`
- [bootstrap()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/bootstrap.py#27-53) and [check_readiness()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/bootstrap.py#54-58): wrap DB calls in UoW context

#### [MODIFY] [sync.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/sync.py)

- Constructor: `uow_factory` instead of 3 repos
- [reconcile_stale_chunks()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/sync.py#31-64) and [full_sync()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/sync.py#65-75): wrap in UoW context

#### [MODIFY] [versioning.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/versioning.py)

- Constructor: `uow_factory` instead of 3 repos
- [activate_version()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/versioning.py#27-57) and [get_active_version_id()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/versioning.py#58-63): wrap in UoW context

#### [MODIFY] [reembed.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/reembed.py)

- Constructor: `uow_factory` instead of 2 repos
- [process_pending()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/services/reembed.py#31-55): wrap in UoW context

#### [MODIFY] [matcher.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/scenarios/matcher.py)

- Constructor: `uow_factory` instead of `scenario_repo`
- [match()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/storage/repositories/scenario.py#26-49): wrap in UoW context

---

### RAG Orchestrator + Embedding Pipeline

#### [MODIFY] [orchestrator.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/orchestrator.py)

- Constructor: `uow_factory` instead of `document_repo` + `version_repo`
- [_build_version_map()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/orchestrator.py#217-233): wrap in UoW context

#### [MODIFY] [pipeline.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/embeddings/pipeline.py)

- Constructor: `uow_factory` instead of `chunk_repo`
- [embed_chunks()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/rag/embeddings/pipeline.py#52-98): wrap in UoW context

---

### Container + Startup

#### [MODIFY] [dependencies.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/dependencies.py)

- [build_rag()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/dependencies.py#307-394): no session parameter. Creates UoW factory from `self.db`, passes to all services/orchestrator
- Remove individual repo attributes from Container
- [shutdown()](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/registry.py#163-185): remove `_rag_session` cleanup (no persistent session)

#### [MODIFY] [main.py](file:///wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/main.py)

- Remove `async with container.db.session()` blocks
- Call `await container.build_rag()` once, no session parameter

## Verification Plan

- `grep` for remaining [session](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/shared/db/connection.py#129-220) parameter in [build_rag](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/dependencies.py#307-394) → should be none
- `grep` for `_session_factory` access outside [DatabaseManager](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/shared/db/connection.py#38-316) → should be none
- `grep` for `async with container.db.session() as session` in [main.py](file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/main.py) → should be none
- All services use `async with self._uow() as uow:` pattern consistently
