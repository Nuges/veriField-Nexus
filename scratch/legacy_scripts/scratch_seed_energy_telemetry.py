import asyncio
import sys
import os
import json
from datetime import datetime, timedelta, timezone
import random
from dotenv import load_dotenv

load_dotenv('backend/.env')
sys.path.append(os.path.abspath('backend'))

from app.db.session import async_session_factory
from app.models.activity import Activity
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

async def main():
    print("=== Seeding Hybrid Energy Telemetry Logs ===")
    async with async_session_factory() as session:
        # Find the HYBRID_ENERGY activity
        result = await session.execute(
            select(Activity).where(Activity.activity_type == "HYBRID_ENERGY")
        )
        activities = result.scalars().all()
        
        target_activity = None
        for act in activities:
            if act.activity_data and act.activity_data.get("site_id") == "VF-EN-LAG-1001":
                target_activity = act
                break
                
        if not target_activity:
            print("Could not find HYBRID_ENERGY activity with site_id='VF-EN-LAG-1001'.")
            return
            
        print(f"Found activity ID: {target_activity.id}")
        
        # Generate 30 days of telemetry logs
        telemetry_log = []
        now = datetime.now(timezone.utc)
        
        for i in range(30):
            date_str = (now - timedelta(days=29-i)).strftime("%Y-%m-%d")
            solar_kwh = round(random.uniform(220.0, 480.0), 2)
            grid_kwh = round(random.uniform(60.0, 180.0), 2)
            diesel_hrs = round(random.uniform(0.5, 3.5), 1)
            battery_soc = round(random.uniform(78.0, 96.0), 1)
            uptime_pct = round(random.uniform(96.0, 100.0), 1)
            
            telemetry_log.append({
                "date": date_str,
                "solar_kwh": solar_kwh,
                "grid_kwh": grid_kwh,
                "diesel_hrs": diesel_hrs,
                "gas_hrs": 0.0,
                "battery_soc": battery_soc,
                "uptime_pct": uptime_pct,
                "faults": [],
                "temp_c": round(random.uniform(27.0, 33.0), 1)
            })
            
        act_data = dict(target_activity.activity_data) if target_activity.activity_data else {}
        act_data["telemetry_log"] = telemetry_log
        target_activity.activity_data = act_data
        
        # Inform SQLAlchemy of JSONB modification
        flag_modified(target_activity, "activity_data")
        
        await session.commit()
        print(f"Successfully seeded {len(telemetry_log)} telemetry logs into activity_data!")

if __name__ == "__main__":
    asyncio.run(main())
