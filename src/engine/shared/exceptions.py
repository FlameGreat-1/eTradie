from __future__ import annotations

from typing import Any


class ETradieBaseError(Exception):

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"{cls}(message={self.message!r}, details={self.details!r})"


class ConfigurationError(ETradieBaseError):
    pass


class ProviderError(ETradieBaseError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class ProviderValidationError(ProviderError):
    pass


class CollectorError(ETradieBaseError):
    pass


class CollectorAllProvidersFailedError(CollectorError):
    pass


class MeteringUnavailableError(ETradieBaseError):
    """Raised by MeteringClient.reserve() on HTTP 503 from the gateway.

    Signals a transient infrastructure condition (DB pool exhaustion,
    seed migration not yet run on a fresh deploy, brief Postgres
    failover) that the engine should treat as fail-closed: do NOT
    proceed with the LLM call. Distinct from QuotaExceededError
    (real cap breach) so the operator log line and the user-facing
    surface render the correct discriminator.

    Attributes:
        retry_after : seconds the gateway recommends waiting before
                      retry. Parsed from the Retry-After header.

    Audit ref: ADMIN-QUOTA-AUDIT-V3-A8.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: int = 5,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details or {})
        self.retry_after = retry_after


class QuotaExceededError(ETradieBaseError):
    """Raised by MeteringClient.reserve() when the user has hit a
    per-tier LLM token cap. The gateway returns a structured 429 body;
    this exception carries the parsed fields so the processor can
    surface a meaningful message and the internal router can map it
    to an HTTP 429 with a Retry-After header.

    Attributes:
        dimension   : which cap was breached (e.g. 'daily_input',
                      'monthly_output', 'per_call_input',
                      'model_not_allowed').
        limit       : the cap value.
        used        : tokens already consumed in the window.
        requested   : tokens the current call would have consumed.
        resets_at   : ISO-8601 UTC timestamp when the window resets.
        retry_after : seconds until the window resets (pre-computed
                      from resets_at for the Retry-After header).
    """

    def __init__(
        self,
        message: str,
        *,
        dimension: str = "",
        limit: int = 0,
        used: int = 0,
        requested: int = 0,
        resets_at: str = "",
        retry_after: int = 60,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details or {})
        self.dimension = dimension
        self.limit = limit
        self.used = used
        self.requested = requested
        self.resets_at = resets_at
        self.retry_after = retry_after


class ProcessorError(ETradieBaseError):
    pass


class ProcessorInsufficientDataError(ProcessorError):
    pass


class StorageError(ETradieBaseError):
    pass


class StorageConnectionError(StorageError):
    pass


class StorageIntegrityError(StorageError):
    pass


class PipelineError(ETradieBaseError):
    pass


class DatabaseError(ETradieBaseError):
    pass


class DatabaseConnectionError(DatabaseError):
    pass


class DatabaseIntegrityError(DatabaseError):
    pass


class DatabaseOperationalError(DatabaseError):
    pass


class DatabaseTimeoutError(DatabaseError):
    pass


class RepositoryError(ETradieBaseError):
    pass


class AuthUserMissingError(ETradieBaseError):
    """Raised when a still-valid JWT references a user that no longer
    exists in ``auth_users``.

    This is a recoverable condition from the client's perspective: the
    SPA should treat it the same way it treats a 401 (clear the local
    session and route to /login). The engine surfaces it as a typed
    exception so call sites that perform an INSERT FK'd to
    ``auth_users`` (e.g. billing_usage upsert) can convert the FK
    violation into a clean HTTP 401 instead of leaking a 500.

    Attributes:
        user_id: The orphaned ``sub`` claim from the JWT. Logged but
            never returned to the client to avoid leaking internal IDs
            to a partially-authenticated caller.
    """

    def __init__(self, user_id: str, *, details: dict | None = None) -> None:
        super().__init__(
            "Authenticated user no longer exists",
            details={**(details or {}), "user_id": user_id},
        )
        self.user_id = user_id


class CacheError(ETradieBaseError):
    pass


class CacheConnectionError(CacheError):
    pass


class CacheTimeoutError(CacheError):
    pass


class CacheValidationError(CacheError):
    pass


class HttpClientError(ETradieBaseError):
    pass


class SchedulerError(ETradieBaseError):
    pass


class SchedulerValidationError(SchedulerError):
    pass


class TracingError(ETradieBaseError):
    pass


class TracingValidationError(TracingError):
    pass


# ══════════════════════════════════════════════════════════
# RAG (Retrieval-Augmented Generation) Errors
# ══════════════════════════════════════════════════════════


class RAGError(ETradieBaseError):
    """Base error for all RAG subsystem failures."""

    pass


class RAGIngestError(RAGError):
    """Failure during document ingestion pipeline (load, normalize, chunk, embed, upsert)."""

    pass


class RAGLoaderError(RAGIngestError):
    """Failure loading a source document from disk or remote."""

    pass


class RAGNormalizationError(RAGIngestError):
    """Failure normalizing source document content."""

    pass


class RAGChunkingError(RAGIngestError):
    """Failure splitting a document into chunks."""

    pass


class RAGValidationError(RAGError):
    """Validation failure for documents, chunks, or scenarios."""

    pass


class RAGEmbeddingError(RAGError):
    """Failure generating or validating embeddings."""

    pass


class RAGEmbeddingProviderError(RAGEmbeddingError):
    """Embedding provider API call failure (timeout, auth, rate limit)."""

    pass


class RAGVectorStoreError(RAGError):
    """Failure communicating with the vector store (ChromaDB)."""

    pass


class RAGVectorStoreConnectionError(RAGVectorStoreError):
    """Cannot connect to the vector store."""

    pass


class RAGVectorStoreUpsertError(RAGVectorStoreError):
    """Failure upserting vectors into the store."""

    pass


class RAGRetrievalError(RAGError):
    """Failure during retrieval pipeline (query, filter, rerank, assemble)."""

    pass


class RAGCoverageError(RAGRetrievalError):
    """Retrieved material does not sufficiently cover the requested context."""

    pass


class RAGConflictError(RAGRetrievalError):
    """Conflicting rules or examples detected across retrieved chunks."""

    pass


class RAGScenarioError(RAGError):
    """Failure in chart scenario handling (loading, indexing, matching)."""

    pass


class RAGKnowledgeBaseError(RAGError):
    """Knowledge base governance failure (missing mandatory assets, version issues)."""

    pass


class RAGBootstrapError(RAGError):
    """Failure during RAG bootstrap or initialization."""

    pass


class RAGVersioningError(RAGError):
    """Document version lifecycle failure (supersession, activation)."""

    pass


class RAGSyncError(RAGError):
    """Failure synchronizing source docs with vector and relational stores."""

    pass
