import asyncio
import sys
from uuid import UUID
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.activity import Activity
from app.services.quantification_engine import QuantificationEngine

async def run():
    async with async_session_factory() as db:
        result = await db.execute(select(Activity).order_by(Activity.created_at.desc()).limit(1))
        activity = result.scalar_one_or_none()
        if not activity:
            print("No activities found")
            return
        
        print("Activity ID:", activity.id)
        print("Activity Status:", activity.status)
        print("Activity Type:", activity.activity_type)
        
        engine = QuantificationEngine(db)
        try:
            calc = await engine.quantify_activity(activity.id, None)
            print("Successfully quantified!")
            print("tCO2e:", calc.tco2e_generated)
            print("Log:", calc.calculation_log)
        except Exception as e:
            print("Quantification failed with exception:", e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
