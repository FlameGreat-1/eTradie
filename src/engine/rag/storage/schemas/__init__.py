"""RAG SQLAlchemy table schemas.

Every schema module in this package is re-exported here so importing
the package alone is enough to populate Base.metadata. Required by
alembic env.py for autogenerate to see the full graph. Audit ref:
FV-M1.
"""
from engine.rag.storage.schemas import chunk  # noqa: F401
from engine.rag.storage.schemas import citation_log  # noqa: F401
from engine.rag.storage.schemas import document  # noqa: F401
from engine.rag.storage.schemas import document_version  # noqa: F401
from engine.rag.storage.schemas import ingest_job  # noqa: F401
from engine.rag.storage.schemas import reembed_queue  # noqa: F401
from engine.rag.storage.schemas import retrieval_log  # noqa: F401
from engine.rag.storage.schemas import scenario  # noqa: F401
