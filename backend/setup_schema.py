import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base
from app.core.config import settings

# Import all models to ensure they are registered with Base.metadata
from app.models import *

async def create_tables():
    db_url = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@34.241.16.247:5432/postgres"
        
    engine = create_async_engine(
        db_url,
        connect_args={
            "ssl": "require",
            "server_settings": {"jit": "off"},
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
    )
    
    async with engine.begin() as conn:
        print("Creating Methodology Registry tables...")
        # Since we use Base.metadata, create_all will create any missing tables.
        await conn.run_sync(Base.metadata.create_all)
        print("Done.")
        
if __name__ == "__main__":
    asyncio.run(create_tables())
