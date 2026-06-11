import asyncio
import sys
import os

sys.path.append(os.path.abspath("."))

from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.models.property import Property
from app.models.sensor_reading import SensorReading

async def main():
    print("Connecting to DB...")
    async with async_session_factory() as session:
        # Check property count and sector types
        prop_count_res = await session.execute(select(func.count(Property.id)))
        prop_count = prop_count_res.scalar()
        print(f"Total properties: {prop_count}")

        props_res = await session.execute(select(Property))
        props = props_res.scalars().all()
        for p in props:
            print(f"Property ID: {p.id}, Name: {p.name}, Type: {p.property_type}, Metrics: {p.sustainability_metrics}")

        # Check sensor reading count
        sensor_count_res = await session.execute(select(func.count(SensorReading.id)))
        sensor_count = sensor_count_res.scalar()
        print(f"Total sensor readings: {sensor_count}")

        # Check sensor readings by device/asset
        if sensor_count > 0:
            agg = await session.execute(
                select(
                    SensorReading.device_id,
                    SensorReading.asset_id,
                    func.count(SensorReading.id)
                ).group_by(SensorReading.device_id, SensorReading.asset_id)
            )
            for row in agg.all():
                print(f"Device: {row[0]}, Asset ID: {row[1]}, Count: {row[2]}")
        else:
            print("No sensor readings found in the database.")

if __name__ == "__main__":
    asyncio.run(main())
