import asyncio
import os
from engine.config import get_settings
from engine.shared.db import DatabaseManager
from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.storage.repositories.chunk import ChunkRepository
from sqlalchemy import select
from engine.rag.storage.schemas.document import DocumentRow

async def main():
    s = get_settings()
    print(f"DEBUG: Using DATABASE_URL: {s.async_database_url}")
    db = DatabaseManager(url=s.async_database_url)
    
    async with db.session() as session:
        doc_repo = DocumentRepository(session)
        
        # Raw query check
        stmt = select(DocumentRow)
        result = await session.execute(stmt)
        all_rows = result.scalars().all()
        print(f"DEBUG: Raw query count: {len(all_rows)}")
        
        for row in all_rows:
            print(f"- Found Document: {row.title} (ID: {row.id}, Status: {row.status}, Type: {row.doc_type})")
            
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
