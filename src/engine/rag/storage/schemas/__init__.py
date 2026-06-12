"""RAG SQLAlchemy table schemas.

Every schema module in this package is re-exported here so importing
the package alone is enough to populate Base.metadata. Required by
alembic env.py for autogenerate to see the full graph. Audit ref:
FV-M1.
"""

from engine.rag.storage.schemas import (
    chunk,  # noqa: F401
    citation_log,  # noqa: F401
    document,  # noqa: F401
    document_version,  # noqa: F401
    ingest_job,  # noqa: F401
    reembed_queue,  # noqa: F401
    retrieval_log,  # noqa: F401
    scenario,  # noqa: F401
)
