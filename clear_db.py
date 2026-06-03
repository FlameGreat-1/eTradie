import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from engine.config import settings

async def main():
    engine = create_async_engine(settings.database_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(text("DELETE FROM macro_snapshots WHERE namespace = 'calendar'"))
        await session.commit()
    print('Postgres cache cleared')

asyncio.run(main())
