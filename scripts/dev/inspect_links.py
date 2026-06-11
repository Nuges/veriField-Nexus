import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def inspect():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Query properties and their activities
        query = text("""
            SELECT p.id, p.name, p.property_type, a.id, a.activity_type, a.activity_data, a.trust_score
            FROM properties p
            LEFT JOIN activities a ON a.property_id = p.id
        """)
        res = await session.execute(query)
        rows = res.all()
        for r in rows:
            p_id, p_name, p_type, a_id, a_type, a_data, score = r
            print(f"Prop: {p_name} ({p_type}) [{p_id}] -> Act: {a_type} [{a_id}] | Score: {score} | Data: {str(a_data)[:80]}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
