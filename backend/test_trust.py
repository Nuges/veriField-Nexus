import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.domains.activities.models import Activity
from app.domains.ai_trust_engine.service import TrustEngineService
import uuid
import sys

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:6543/postgres")
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with Session() as db:
        stmt = select(Activity).where(Activity.id == uuid.UUID('4f90f883-b52b-4b34-be52-cc09e07824d2'))
        result = await db.execute(stmt)
        activity = result.scalar_one_or_none()
        
        if not activity:
            print("Activity not found")
            return
            
        trust_service = TrustEngineService(db)
        try:
            score, findings = await trust_service.calculate_trust(activity)
            print(f"Score: {score}, findings: {findings}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
