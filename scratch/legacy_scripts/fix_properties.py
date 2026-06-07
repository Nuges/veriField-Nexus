import asyncio
from app.db.session import async_session_maker
from app.models.property import Property
from sqlalchemy import select

async def fix_properties():
    async with async_session_maker() as session:
        result = await session.execute(select(Property))
        properties = result.scalars().all()
        
        count = 0
        for prop in properties:
            if not prop.sustainability_metrics or prop.sustainability_metrics == {}:
                prop.sustainability_metrics = {
                    "energy_score": "Pending",
                    "carbon_offset_kg": "Calculating...",
                    "status": "Awaiting Review"
                }
                count += 1
                
        await session.commit()
        print(f"✅ Successfully updated {count} existing properties with default metrics!")

if __name__ == "__main__":
    asyncio.run(fix_properties())
