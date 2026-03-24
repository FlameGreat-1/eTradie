import asyncio
import os
from engine.config import get_settings
from engine.shared.db import DatabaseManager
from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.storage.repositories.chunk import ChunkRepository


async def main():
    s = get_settings()
    db = DatabaseManager(url=s.async_database_url)

    async with db.session() as session:
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)

        docs = await doc_repo.list_all()
        print(f"Total documents in DB: {len(docs)}")

        for doc in docs:
            chunks = await chunk_repo.get_by_document(doc.id)
            pending = [c for c in chunks if c.embedding_status == "pending"]
            completed = [c for c in chunks if c.embedding_status == "completed"]
            print(
                f"- {doc.title} ({doc.doc_type}): {len(chunks)} chunks total, {len(pending)} pending, {len(completed)} completed"
            )

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
