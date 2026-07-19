import asyncio
import os
import sys

from app.db.session import async_session_factory
from app.domains.activities.models import Activity
from app.domains.ai_trust_engine.service import TrustEngineService
from sqlalchemy import select
import uuid

async def main():
    async with async_session_factory() as db:
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
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
