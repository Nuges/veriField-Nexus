import asyncio
import sys
import os
import random
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath("."))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.property import Property
from app.models.sensor_reading import SensorReading

async def main():
    print("Connecting to DB to seed energy sensor readings...")
    async with async_session_factory() as session:
        # Find all HYBRID_ENERGY and commercial properties
        result = await session.execute(
            select(Property).where(
                Property.property_type.in_(["HYBRID_ENERGY", "commercial"])
            )
        )
        properties = result.scalars().all()
        
        if not properties:
            print("No energy or commercial properties found!")
            return
            
        print(f"Found {len(properties)} properties to seed sensor readings for.")
        
        # Clear any existing sensor readings for these properties to avoid clutter
        for p in properties:
            print(f"Seeding property: {p.name} ({p.id})")
            
            # Generate 168 readings (hourly for 7 days)
            now = datetime.now(timezone.utc)
            device_id = f"ESP32-EN-{str(p.id)[:4].upper()}"
            
            readings = []
            for h in range(168):
                timestamp = now - timedelta(hours=h)
                temp = round(random.uniform(38.0, 54.0), 1)
                battery = round(random.uniform(12.8, 14.2), 2)
                usage = random.random() < 0.95 # 95% usage rate
                
                reading = SensorReading(
                    asset_id=p.id,
                    device_id=device_id,
                    temperature=temp,
                    usage_flag=usage,
                    battery_voltage=battery,
                    timestamp=timestamp
                )
                readings.append(reading)
                
            session.add_all(readings)
            print(f"Added {len(readings)} readings for device {device_id} on property {p.name}")
            
        await session.commit()
        print("Successfully seeded all energy sensor readings!")

if __name__ == "__main__":
    asyncio.run(main())
