import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def inspect():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Inspect properties
        res_props = await session.execute(text("SELECT id, name, property_type, address, sustainability_metrics FROM properties"))
        props = res_props.all()
        print(f"=== PROPERTIES ({len(props)} total) ===")
        for p in props:
            p_id, name, p_type, address, metrics = p
            print(f"ID: {p_id} | Name: {name} | Type: {p_type} | Address: {address} | Metrics: {metrics}")
            
        # Inspect activities
        res_acts = await session.execute(text("SELECT id, activity_type, activity_data, trust_score, status FROM activities"))
        acts = res_acts.all()
        print(f"\n=== ACTIVITIES ({len(acts)} total) ===")
        for a in acts:
            a_id, a_type, a_data, score, status = a
            print(f"ID: {a_id} | Type: {a_type} | Score: {score} | Status: {status} | Data: {str(a_data)[:100]}...")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
