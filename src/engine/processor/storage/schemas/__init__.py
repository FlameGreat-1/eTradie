"""Processor SQLAlchemy table schemas.

Every schema module in this package is re-exported here so importing
the package alone is enough to populate Base.metadata. Required by
alembic env.py for autogenerate to see the full graph. Audit ref:
FV-M1.
"""

from engine.processor.storage.schemas import (
    broker_connection_schema,  # noqa: F401
    llm_connection_schema,  # noqa: F401
    processor_schema,  # noqa: F401
)
